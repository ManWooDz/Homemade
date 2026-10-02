import os
import sys
import unittest
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import get_db
from database.models import (
    Base,
    BaseRecipe,
    Favorite,
    GenerateHistory,
    Rating,
    RefreshToken,
    User,
)
from history_repository import insert_generate_history
from main import app
from nutrition.calculator import NutritionResult

APPROVED = {
    "recipe_name": "Thai Basil Pork",
    "servings": 2,
    "adjusted_ingredients": ["หมูสับ 200 กรัม", "น้ำมัน 1 ช้อนโต๊ะ"],
    "diet_tags": ["Thai"],
    "nutrition": {"basis": "per_serving", "calories": 400, "protein_g": 20, "carbs_g": 10, "fat_g": 20},
    "instructions": ["1. ตั้งกระทะใส่น้ำมันแล้วผัดหมู"],
    "safety_warning": "ระวังความร้อน",
}


class HistoryEndpointTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[
                User.__table__,
                RefreshToken.__table__,
                BaseRecipe.__table__,
                GenerateHistory.__table__,
                Rating.__table__,
                Favorite.__table__,
            ],
        )
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = self.session_local()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.origin = {"Origin": "http://127.0.0.1:5173"}

    def tearDown(self):
        app.dependency_overrides.clear()

    def login(self, email, password="hunter22"):
        client = TestClient(app)
        client.post("/api/auth/register", json={"email": email, "password": password}, headers=self.origin)
        client.post("/api/auth/login", data={"username": email, "password": password}, headers=self.origin)
        return client

    def user_id(self, email):
        with self.session_local() as db:
            return db.execute(select(User.id).where(User.email == email)).scalar_one()

    def seed_history(self, email):
        with self.session_local() as db:
            return insert_generate_history(
                db, user_id=self.user_id(email), request_recipe={"name": "Custom"}, final_output=deepcopy(APPROVED)
            )


class HistoryEndpointTests(HistoryEndpointTestCase):
    def setUp(self):
        super().setUp()
        rating_embedding_patcher = patch(
            "main.embed_rated_history_best_effort", new=AsyncMock(return_value=None)
        )
        self.mock_rating_embedding = rating_embedding_patcher.start()
        self.addCleanup(rating_embedding_patcher.stop)
        self.alice = self.login("alice@example.com")
        self.bob = self.login("bob@example.com")
        self.alice_history = self.seed_history("alice@example.com")

    def rate(self, client, history_id, body):
        return client.put(f"/api/history/{history_id}/rating", json=body, headers=self.origin)

    def test_list_returns_only_own_rows(self):
        alice_rows = self.alice.get("/api/history").json()["data"]
        bob_rows = self.bob.get("/api/history").json()["data"]
        self.assertEqual([row["id"] for row in alice_rows], [self.alice_history])
        self.assertEqual(bob_rows, [])

    def test_other_users_or_missing_history_is_404(self):
        for history_id in (self.alice_history, 99999):
            with self.subTest(history_id=history_id):
                self.assertEqual(self.rate(self.bob, history_id, {"stars": 5}).status_code, 404)
                self.assertEqual(
                    self.bob.put(f"/api/history/{history_id}/favorite", headers=self.origin).status_code, 404
                )
                self.assertEqual(
                    self.bob.delete(f"/api/history/{history_id}/favorite", headers=self.origin).status_code, 404
                )
        self.assertIsNone(self.alice.get("/api/history").json()["data"][0]["rating"])
        self.assertFalse(self.alice.get("/api/history").json()["data"][0]["is_favorite"])

    def test_rating_upsert_overwrites(self):
        first = self.rate(self.alice, self.alice_history, {"stars": 2, "tag": "Meh", "feedback": "เค็มไป"})
        self.assertEqual(first.status_code, 200)
        second = self.rate(self.alice, self.alice_history, {"stars": 5, "tag": "Great", "feedback": "เผ็ดไป 🌶️ → ลดพริก"})
        self.assertEqual(second.json()["data"], {"stars": 5, "tag": "Great", "feedback": "เผ็ดไป 🌶️ → ลดพริก"})
        # updated_at is not asserted: SQLite CURRENT_TIMESTAMP has 1-second resolution.
        rating = self.alice.get("/api/history").json()["data"][0]["rating"]
        self.assertEqual(rating, {"stars": 5, "tag": "Great", "feedback": "เผ็ดไป 🌶️ → ลดพริก"})
        with self.session_local() as db:
            self.assertEqual(len(db.execute(select(Rating)).scalars().all()), 1)

    def test_blank_feedback_is_stored_as_null(self):
        for feedback in ("", "   "):
            with self.subTest(feedback=feedback):
                res = self.rate(self.alice, self.alice_history, {"stars": 3, "feedback": feedback})
                self.assertEqual(res.json()["data"]["feedback"], None)

    def test_feedback_length_boundary(self):
        ok = self.rate(self.alice, self.alice_history, {"stars": 3, "feedback": "ก" * 240})
        self.assertEqual(ok.status_code, 200)
        too_long = self.rate(self.alice, self.alice_history, {"stars": 3, "feedback": "ก" * 241})
        self.assertEqual(too_long.status_code, 422)

    def test_invalid_rating_bodies_are_422(self):
        for body in (
            {"stars": 0},
            {"stars": 6},
            {"stars": "5"},
            {"stars": 5, "tag": "Amazing"},
            {"stars": 5, "user_id": 1},
            {},
        ):
            with self.subTest(body=body):
                self.assertEqual(self.rate(self.alice, self.alice_history, body).status_code, 422)

    def test_favorite_put_and_delete_are_idempotent(self):
        url = f"/api/history/{self.alice_history}/favorite"
        for _ in range(2):
            res = self.alice.put(url, headers=self.origin)
            self.assertEqual(res.json()["data"], {"is_favorite": True})
        self.assertTrue(self.alice.get("/api/history").json()["data"][0]["is_favorite"])
        for _ in range(2):
            res = self.alice.delete(url, headers=self.origin)
            self.assertEqual(res.json()["data"], {"is_favorite": False})
        self.assertFalse(self.alice.get("/api/history").json()["data"][0]["is_favorite"])

    def test_out_of_range_history_ids_are_422_and_max_valid_id_is_404(self):
        # Postgres binds ids as INTEGER; anything above 2**31-1 would raise
        # DataError -> 500 if it reached the DB, so validation must stop it.
        for history_id in (2147483648, 0):
            with self.subTest(history_id=history_id):
                self.assertEqual(self.rate(self.alice, history_id, {"stars": 5}).status_code, 422)
                self.assertEqual(
                    self.alice.put(f"/api/history/{history_id}/favorite", headers=self.origin).status_code, 422
                )
                self.assertEqual(
                    self.alice.delete(f"/api/history/{history_id}/favorite", headers=self.origin).status_code, 422
                )
        top = 2147483647
        self.assertEqual(self.rate(self.alice, top, {"stars": 5}).status_code, 404)
        self.assertEqual(self.alice.put(f"/api/history/{top}/favorite", headers=self.origin).status_code, 404)
        self.assertEqual(self.alice.delete(f"/api/history/{top}/favorite", headers=self.origin).status_code, 404)

    def test_requires_login(self):
        anon = TestClient(app)
        self.assertEqual(anon.get("/api/history").status_code, 401)
        self.assertEqual(self.rate(anon, self.alice_history, {"stars": 5}).status_code, 401)
        self.assertEqual(anon.put(f"/api/history/{self.alice_history}/favorite", headers=self.origin).status_code, 401)

    def test_writes_require_trusted_origin(self):
        res = self.alice.put(f"/api/history/{self.alice_history}/rating", json={"stars": 5})
        self.assertEqual(res.status_code, 403)
        res = self.alice.put(f"/api/history/{self.alice_history}/favorite")
        self.assertEqual(res.status_code, 403)
        res = self.alice.delete(f"/api/history/{self.alice_history}/favorite")
        self.assertEqual(res.status_code, 403)


_STUB_NUTRITION = NutritionResult(
    nutrition={"basis": "per_serving", "calories": 1.0, "protein_g": 1.0, "carbs_g": 1.0, "fat_g": 1.0},
    partially_estimated=False,
    partially_estimated_reasons=[],
)


# Copied verbatim from test_generate_handler.VALID_RECIPE: this recipe paired
# with the "minced pork" request below is proven to pass all six validation
# steps, so a failure here is about history, not validation.
GENERATED = {
    "recipe_name": "Thai Basil Pork",
    "servings": 2,
    "adjusted_ingredients": [
        "หมูสับ 200 กรัม",
        "ใบกะเพรา 1 ถ้วย",
        "น้ำมัน 1 ช้อนโต๊ะ",
    ],
    "diet_tags": ["Thai"],
    "nutrition": {
        "basis": "per_serving",
        "calories": 420,
        "protein_g": 28,
        "carbs_g": 18,
        "fat_g": 24,
    },
    "instructions": [
        "1. ตั้งกระทะใส่น้ำมันแล้วผัดหมูให้สุก",
        "2. ใส่ใบกะเพรา",
    ],
    "safety_warning": "ระวังความร้อนขณะประกอบอาหาร",
}


class GenerateWritesHistoryEndToEndTests(HistoryEndpointTestCase):
    """Deviation from the spec's wording ("a stand-in that fails the test if
    called"): the Nutrition Engine block legitimately calls SessionLocal()
    and swallows every exception, so a raising stand-in would be silently
    caught and prove nothing. A MagicMock gives the same guarantee — no
    connection to the dev Postgres — without that false signal.

    The history writer is NOT patched here. Empty allergy prefs mean
    resolve_blocks_for_request returns before touching SessionLocal
    (main.py:676); the Nutrition Engine block still calls SessionLocal(),
    so it is replaced with a MagicMock to guarantee nothing reaches the dev
    Postgres. compute_recipe_nutrition is patched, so the mock session is
    never queried."""

    def setUp(self):
        super().setUp()
        personalization_patcher = patch(
            "main.get_personalization_for_request",
            new=AsyncMock(return_value=None),
        )
        self.mock_personalization = personalization_patcher.start()
        self.addCleanup(personalization_patcher.stop)

    def generate(self, client, extra_body=None, headers=None):
        body = {
            "recipe": {"name": "Custom Recipe from Fridge"},
            "ingredients": [{"id": 1, "name": "minced pork"}],
            "preferences": {"allergy": "", "taste": "", "equipment": "", "extra": ""},
        }
        body.update(extra_body or {})
        with patch("main.call_agentic_llm", return_value=deepcopy(GENERATED)), \
                patch("main.compute_recipe_nutrition", return_value=_STUB_NUTRITION), \
                patch("main.SessionLocal", MagicMock()):
            return client.post(
                "/api/generate-recipe-text",
                json=body,
                headers=self.origin if headers is None else headers,
            )

    def test_history_row_belongs_to_cookie_user(self):
        alice = self.login("alice@example.com")
        bob = self.login("bob@example.com")

        # A spoofed user_id in the body must be ignored.
        res = self.generate(alice, extra_body={"user_id": self.user_id("bob@example.com")})
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertIsInstance(data["history_id"], int)
        self.assertEqual(
            data["personalization"],
            {"applied": False, "positives": 0, "negatives": 0},
        )

        alice_rows = alice.get("/api/history").json()["data"]
        self.assertEqual([row["id"] for row in alice_rows], [data["history_id"]])
        self.assertEqual(alice_rows[0]["recipe_name"], "Thai Basil Pork")
        self.assertNotIn("history_id", alice_rows[0]["recipe_data"])
        self.assertNotIn("personalization", alice_rows[0]["recipe_data"])
        self.assertNotIn("personalization", alice_rows[0])
        self.assertEqual(bob.get("/api/history").json()["data"], [])

    def test_generate_requires_login(self):
        self.assertEqual(self.generate(TestClient(app)).status_code, 401)

    def test_generate_requires_trusted_origin(self):
        alice = self.login("alice@example.com")
        self.assertEqual(self.generate(alice, headers={}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
