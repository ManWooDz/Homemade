import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import get_db
from database.models import Notification, Base, RefreshToken, User, UserIngredient
from main import app
from auth import hash_password


class UserIngredientsEndpointTests(unittest.TestCase):
    def _edit_fixture(self):
        client = TestClient(app)
        self._register_and_login(client, "edit@example.com")
        nutrition = {"basis": "per_100g_or_ml", "calories": 42}
        created = client.post("/api/user-ingredients", headers=self.origin_headers, json={
            "name": "original", "category": "Other", "image": "original.png",
            "nutrition_data": nutrition, "quantity_amount": 2, "quantity_unit": "ชิ้น",
        }).json()["data"]
        payload = {"name": "  edited  ", "category": "Vegetables", "expiry_date": "2026-10-20", "quantity_amount": 500, "quantity_unit": "กรัม"}
        return client, created, payload

    def test_edit_updates_same_row_and_preserves_product_data(self):
        client, created, payload = self._edit_fixture()
        url = f'/api/user-ingredients/{created["id"]}'
        res = client.put(url, json=payload, headers=self.origin_headers)
        self.assertEqual(res.status_code, 200)
        updated = res.json()["data"]
        self.assertEqual(updated["id"], created["id"])
        self.assertEqual(updated["name"], "edited")
        self.assertEqual(updated["category"], "Vegetables")
        self.assertEqual(updated["expiry_date"], payload["expiry_date"])
        self.assertEqual(updated["quantity_amount"], 500)
        self.assertEqual(updated["quantity_unit"], "กรัม")
        for field in ("image", "nutrition_data"):
            self.assertEqual(updated[field], created[field])
        payload.update(expiry_date=None, quantity_amount=None, quantity_unit=None)
        self.assertEqual(client.put(url, json=payload, headers=self.origin_headers).status_code, 200)
        rows = client.get("/api/user-ingredients").json()["data"]
        self.assertEqual(len(rows), 1)
        for field in ("expiry_date", "quantity_amount", "quantity_unit"):
            self.assertIsNone(rows[0][field])

    def test_edit_rejects_invalid_values_without_changing_row(self):
        client, created, payload = self._edit_fixture()
        cases = [{"name": " "}, {"name": "x" * 201}, {"name": True}, {"category": "arbitrary"},
                 {"expiry_date": "2026-02-30"}, {"quantity_amount": 0}, {"quantity_amount": -1},
                 {"quantity_amount": 100001}, {"quantity_amount": True}, {"quantity_amount": "NaN"},
                 {"quantity_unit": "unknown"}, {"quantity_amount": None}, {"image": "replace.png"},
                 {"nutrition_data": None}, {"user_id": 42}]
        for invalid in cases:
            with self.subTest(invalid=invalid):
                res = client.put(f'/api/user-ingredients/{created["id"]}', json={**payload, **invalid}, headers=self.origin_headers)
                self.assertEqual(res.status_code, 422)
        self.assertEqual(client.get("/api/user-ingredients").json()["data"], [created])

    def test_edit_requires_auth_origin_and_owner(self):
        client, created, payload = self._edit_fixture()
        url = f'/api/user-ingredients/{created["id"]}'
        self.assertEqual(TestClient(app).put(url, json=payload, headers=self.origin_headers).status_code, 401)
        for headers in ({}, {"Origin": "https://untrusted.example"}):
            self.assertEqual(client.put(url, json=payload, headers=headers).status_code, 403)
        other = TestClient(app)
        self._register_and_login(other, "otheredit@example.com")
        self.assertEqual(other.put(url, json=payload, headers=self.origin_headers).status_code, 404)
        self.assertEqual(client.put("/api/user-ingredients/999999", json=payload, headers=self.origin_headers).status_code, 404)
        self.assertEqual(client.get("/api/user-ingredients").json()["data"], [created])

    def test_edit_rolls_back_commit_failure_and_hides_internal_error(self):
        client, created, payload = self._edit_fixture()
        with patch("fridge_repository.Session.commit", side_effect=RuntimeError("private DB failure")):
            res = client.put(f'/api/user-ingredients/{created["id"]}', json=payload, headers=self.origin_headers)
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.json(), {"detail": "Could not save ingredient"})
        self.assertEqual(client.get("/api/user-ingredients").json()["data"], [created])

    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine, tables=[User.__table__, Notification.__table__, RefreshToken.__table__, UserIngredient.__table__]
        )
        test_session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = test_session_local()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.origin_headers = {"Origin": "http://127.0.0.1:5173"}

    def tearDown(self):
        app.dependency_overrides.clear()

    def _register_and_login(self, client, email, password="hunter22"):
        with sessionmaker(bind=self.engine)() as db:
            db.add(User(email=email, hashed_password=hash_password(password)))
            db.commit()
        return client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
            headers=self.origin_headers,
        )

    def test_get_is_401_without_login(self):
        client = TestClient(app)
        res = client.get("/api/user-ingredients")
        self.assertEqual(res.status_code, 401)

    def test_post_is_401_without_login(self):
        client = TestClient(app)
        res = client.post(
            "/api/user-ingredients",
            json={"name": "egg", "category": "Other"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 401)

    def test_delete_is_401_without_login(self):
        client = TestClient(app)
        res = client.delete("/api/user-ingredients/1", headers=self.origin_headers)
        self.assertEqual(res.status_code, 401)

    def test_authenticated_crud_cycle_works(self):
        client = TestClient(app)
        self._register_and_login(client, "cruduser@example.com")

        create_res = client.post(
            "/api/user-ingredients",
            json={"name": "egg", "category": "Other"},
            headers=self.origin_headers,
        )
        self.assertEqual(create_res.status_code, 200)
        ingredient_id = create_res.json()["data"]["id"]

        list_res = client.get("/api/user-ingredients")
        self.assertEqual(list_res.status_code, 200)
        names = [row["name"] for row in list_res.json()["data"]]
        self.assertIn("egg", names)

        delete_res = client.delete(
            f"/api/user-ingredients/{ingredient_id}",
            headers=self.origin_headers,
        )
        self.assertEqual(delete_res.status_code, 200)

        list_after_delete = client.get("/api/user-ingredients")
        names_after = [row["name"] for row in list_after_delete.json()["data"]]
        self.assertNotIn("egg", names_after)

    def test_two_users_do_not_see_each_others_ingredients(self):
        # This is the actual point of the Phase 2 migration: before it, every
        # request resolved to the same dev@local user regardless of who was
        # logged in.
        client_a = TestClient(app)
        self._register_and_login(client_a, "usera@example.com")
        client_a.post(
            "/api/user-ingredients",
            json={"name": "tofu", "category": "Other"},
            headers=self.origin_headers,
        )

        client_b = TestClient(app)
        self._register_and_login(client_b, "userb@example.com")
        client_b.post(
            "/api/user-ingredients",
            json={"name": "basil", "category": "Vegetables"},
            headers=self.origin_headers,
        )

        list_a = client_a.get("/api/user-ingredients").json()["data"]
        list_b = client_b.get("/api/user-ingredients").json()["data"]

        names_a = [row["name"] for row in list_a]
        names_b = [row["name"] for row in list_b]

        self.assertIn("tofu", names_a)
        self.assertNotIn("basil", names_a)
        self.assertIn("basil", names_b)
        self.assertNotIn("tofu", names_b)

    def test_delete_cannot_cross_user_boundary(self):
        client_a = TestClient(app)
        self._register_and_login(client_a, "ownera@example.com")
        create_res = client_a.post(
            "/api/user-ingredients",
            json={"name": "shrimp", "category": "Other"},
            headers=self.origin_headers,
        )
        ingredient_id = create_res.json()["data"]["id"]

        client_b = TestClient(app)
        self._register_and_login(client_b, "ownerb@example.com")
        delete_res = client_b.delete(
            f"/api/user-ingredients/{ingredient_id}",
            headers=self.origin_headers,
        )
        self.assertEqual(delete_res.json()["status"], "error")

        still_there = client_a.get("/api/user-ingredients").json()["data"]
        names = [row["name"] for row in still_there]
        self.assertIn("shrimp", names)

    def test_post_with_expiry_date_stores_and_returns_it(self):
        client = TestClient(app)
        self._register_and_login(client, "expiryuser@example.com")
        create_res = client.post(
            "/api/user-ingredients",
            json={"name": "milk", "category": "Other", "expiry_date": "2099-01-01"},
            headers=self.origin_headers,
        )
        self.assertEqual(create_res.status_code, 200)
        self.assertEqual(create_res.json()["data"]["expiry_date"], "2099-01-01")

    def test_post_with_explicit_null_expiry_date_succeeds(self):
        client = TestClient(app)
        self._register_and_login(client, "nullexpiryuser@example.com")
        create_res = client.post(
            "/api/user-ingredients",
            json={"name": "rice", "category": "Other", "expiry_date": None},
            headers=self.origin_headers,
        )
        self.assertEqual(create_res.status_code, 200)
        self.assertIsNone(create_res.json()["data"]["expiry_date"])

    def test_post_with_nutrition_data_stores_and_returns_it(self):
        client = TestClient(app)
        self._register_and_login(client, "nutritionuser@example.com")
        nutrition = {"basis": "per_100g_or_ml", "calories": 42.0, "protein_g": 0.0, "carbs_g": 10.6, "fat_g": 0.0}
        create_res = client.post(
            "/api/user-ingredients",
            json={"name": "cola", "category": "Other", "nutrition_data": nutrition},
            headers=self.origin_headers,
        )
        self.assertEqual(create_res.status_code, 200)
        self.assertEqual(create_res.json()["data"]["nutrition_data"], nutrition)

    def test_post_with_unknown_nutrition_data_field_is_422(self):
        client = TestClient(app)
        self._register_and_login(client, "badnutritionuser@example.com")
        create_res = client.post(
            "/api/user-ingredients",
            json={
                "name": "cola",
                "category": "Other",
                "nutrition_data": {"basis": "per_100g_or_ml", "sneaky_field": "x"},
            },
            headers=self.origin_headers,
        )
        self.assertEqual(create_res.status_code, 422)

    def test_post_with_quantity_stores_and_returns_it(self):
        client = TestClient(app)
        self._register_and_login(client, "quantityuser@example.com")
        create_res = client.post(
            "/api/user-ingredients",
            json={"name": "milk", "category": "Other", "quantity_amount": 1.5, "quantity_unit": "ลิตร"},
            headers=self.origin_headers,
        )
        self.assertEqual(create_res.status_code, 200)
        data = create_res.json()["data"]
        self.assertEqual(data["quantity_amount"], 1.5)
        self.assertEqual(data["quantity_unit"], "ลิตร")

    def test_post_with_zero_or_negative_quantity_is_422(self):
        client = TestClient(app)
        self._register_and_login(client, "zeroquantity@example.com")
        for bad_amount in (0, -1):
            res = client.post(
                "/api/user-ingredients",
                json={"name": "milk", "category": "Other", "quantity_amount": bad_amount, "quantity_unit": "ขวด"},
                headers=self.origin_headers,
            )
            self.assertEqual(res.status_code, 422, f"amount={bad_amount}")

    def test_post_with_nan_quantity_is_422_not_500(self):
        client = TestClient(app)
        self._register_and_login(client, "nanquantity@example.com")
        # Raw body, not json.dumps -- Python's json module (and thus a
        # real client) can emit literal NaN, which json.loads() accepts by
        # default. Pydantic v2 floats allow inf/nan unless told otherwise,
        # and a stored NaN would break JSON serialization on every future
        # GET for this user (Starlette's JSONResponse uses allow_nan=False,
        # outside this handler's try/except) -- so this must be rejected
        # here, not merely "handled gracefully" downstream.
        res = client.post(
            "/api/user-ingredients",
            content='{"name": "milk", "category": "Other", "quantity_amount": NaN, "quantity_unit": "ขวด"}',
            headers={**self.origin_headers, "Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 422)

    def test_post_with_nan_nested_inside_a_different_errors_input_is_422_not_500(self):
        client = TestClient(app)
        self._register_and_login(client, "nannestedmissingname@example.com")
        # "name" is missing entirely -- that error's own "input" is the
        # WHOLE parent dict (including the NaN quantity_amount nested
        # inside it), not the bare NaN scalar. A non-recursive sanitize
        # (only checking the top-level "input" value) misses this: the
        # missing-name error's input is a dict, gets skipped, and the
        # nested NaN inside it still crashes json.dumps downstream.
        res = client.post(
            "/api/user-ingredients",
            content='{"category": "Other", "quantity_amount": NaN}',
            headers={**self.origin_headers, "Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 422)

    def test_post_with_nan_inside_nested_nutrition_data_is_422_not_500(self):
        client = TestClient(app)
        self._register_and_login(client, "nannestednutrition@example.com")
        # Same "nested, not top-level" shape as above, via a different
        # nested model: NutritionData.calories = NaN. Also proves
        # NutritionData's own allow_inf_nan=False actually rejects it at
        # the field level, not just that the response doesn't crash.
        res = client.post(
            "/api/user-ingredients",
            content='{"name": "milk", "category": "Other", "nutrition_data": {"basis": "per_100g_or_ml", "calories": NaN}}',
            headers={**self.origin_headers, "Content-Type": "application/json"},
        )
        self.assertEqual(res.status_code, 422)

    def test_post_with_invalid_quantity_unit_is_422(self):
        client = TestClient(app)
        self._register_and_login(client, "badunit@example.com")
        res = client.post(
            "/api/user-ingredients",
            json={"name": "milk", "category": "Other", "quantity_amount": 1, "quantity_unit": "not-a-real-unit"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 422)

    def test_post_with_unit_but_no_amount_is_422(self):
        client = TestClient(app)
        self._register_and_login(client, "unitnoamount@example.com")
        res = client.post(
            "/api/user-ingredients",
            json={"name": "milk", "category": "Other", "quantity_unit": "ขวด"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 422)

    def test_post_with_amount_but_no_unit_succeeds(self):
        client = TestClient(app)
        self._register_and_login(client, "amountnounit@example.com")
        res = client.post(
            "/api/user-ingredients",
            json={"name": "eggs", "category": "Other", "quantity_amount": 6},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["quantity_amount"], 6)
        self.assertIsNone(res.json()["data"]["quantity_unit"])

    def test_post_without_trusted_origin_is_403(self):
        client = TestClient(app)
        self._register_and_login(client, "csrfuser@example.com")
        res = client.post("/api/user-ingredients", json={"name": "egg", "category": "Other"})
        self.assertEqual(res.status_code, 403)

    def test_delete_without_trusted_origin_is_403(self):
        client = TestClient(app)
        self._register_and_login(client, "csrfdelete@example.com")
        create_res = client.post(
            "/api/user-ingredients",
            json={"name": "egg", "category": "Other"},
            headers=self.origin_headers,
        )
        ingredient_id = create_res.json()["data"]["id"]
        res = client.delete(f"/api/user-ingredients/{ingredient_id}")
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
