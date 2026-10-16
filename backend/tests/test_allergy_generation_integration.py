"""Authenticated application integration with isolated DB/provider boundaries."""
import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from allergen_kg.fixtures import add_edges
from auth import create_access_token
from database.db import get_db
from database.models import (AllergenEdge, Base, BaseRecipe, Favorite, GenerateHistory,
                             IngredientNode, IngredientNutrition, IngredientNutritionAlias, Notification, Rating, User)
from database.seed_allergen_graph import seed_allergen_graph
from main import app


SAFE = {
    "recipe_name": "Pork", "servings": 1,
    "adjusted_ingredients": ["หมูสับ 100 กรัม", "น้ำมัน 1 ช้อนโต๊ะ"],
    "instructions": ["ใส่น้ำมันผัดหมูให้สุก"], "diet_tags": ["Thai"],
    "safety_warning": "ระวังความร้อน",
    "nutrition": {"basis": "per_serving", "calories": 300, "protein_g": 15, "carbs_g": 10, "fat_g": 10},
}
KEYS = ("shrimp", "peanut", "milk", "egg", "gluten", "shellfish", "fish", "soy", "nut", "sesame")


class AllergyGenerationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:",
                                    connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine, tables=[User.__table__, BaseRecipe.__table__,
            GenerateHistory.__table__, Rating.__table__, Favorite.__table__, Notification.__table__,
            IngredientNode.__table__, AllergenEdge.__table__,
            IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.sessions = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        with self.sessions() as db:
            db.add(User(id=7, email="allergy-integration@example.test", hashed_password=None))
            db.commit()

        self.original_overrides = app.dependency_overrides.copy()
        self.addCleanup(self.restore_overrides)
        app.dependency_overrides[get_db] = self.get_db
        self.factory_patch = patch("main.SessionLocal", self.sessions)
        self.factory_patch.start()
        self.addCleanup(self.factory_patch.stop)
        self.provider = MagicMock()
        self.provider_patch = patch("main.client", SimpleNamespace(models=self.provider))
        self.provider_patch.start()
        self.addCleanup(self.provider_patch.stop)
        self.history_queries = []
        event.listen(self.engine, "before_cursor_execute", self.record_history_query)
        self.http = TestClient(app)
        self.addCleanup(self.http.close)
        self.http.cookies.set("access_token", create_access_token(7))
        self.headers = {"Origin": "http://127.0.0.1:5173"}

    def get_db(self):
        with self.sessions() as db:
            yield db

    def restore_overrides(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.original_overrides)

    def record_history_query(self, connection, cursor, statement, parameters, context, executemany):
        if "generate_history" in statement.lower():
            self.history_queries.append(statement)

    def generate(self, allergies, *, extra_ingredients=(), recipe_name="Custom"):
        return self.http.post("/api/generate-recipe-text", headers=self.headers, json={
            "recipe": {"name": recipe_name}, "ingredients": [{"name": name} for name in ("หมูสับ", *extra_ingredients)],
            "preferences": {"allergies": allergies, "taste": "", "equipment": "", "extra": ""},
        })

    def test_partial_graph_stops_before_provider_and_history_work(self):
        with self.sessions() as db:
            add_edges(db, [("crab", "allergen:shellfish")])
        response = self.generate("shellfish")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("code"), "allergy_validation_unavailable")
        self.assertEqual(self.history_queries, [])
        self.provider.generate_content.assert_not_called()

    def test_each_key_refuses_empty_partial_and_unavailable_graphs(self):
        for state in ("empty", "partial", "unavailable"):
            if state == "partial":
                with self.sessions() as db:
                    add_edges(db, [(name, "allergen:" + key) for key, name in zip(KEYS,
                        ("shrimp", "peanut", "milk", "egg", "wheat", "crab", "fish", "soy", "almond", "sesame"))])
            with patch("main.SessionLocal", None if state == "unavailable" else self.sessions):
                for key in KEYS:
                    with self.subTest(state=state, key=key):
                        response = self.generate("ถั่วเปลือกแข็ง" if key == "nut" else key)
                        self.assertEqual(response.json().get("code"), "allergy_validation_unavailable")
        self.assertEqual(self.history_queries, [])
        self.provider.generate_content.assert_not_called()

    def test_real_auth_same_origin_and_ambiguous_wire_input_stop_before_work(self):
        self.http.cookies.clear()
        self.assertEqual(self.generate("sesame").status_code, 401)
        self.http.cookies.set("access_token", "invalid-token")
        self.assertEqual(self.generate("sesame").status_code, 401)
        self.http.cookies.set("access_token", create_access_token(7))
        self.headers = {"Origin": "https://untrusted.example"}
        self.assertEqual(self.generate("sesame").status_code, 403)
        self.headers = {"Origin": "http://127.0.0.1:5173"}
        for allergies, status in (("sesame", "success"), ("ไม่แพ้นม", "success"), ("ลดแป้ง", "error")):
            response = self.http.post("/api/validate-allergy-preferences", headers=self.headers,
                                      json={"preferences": {"allergies": allergies}})
            self.assertEqual(response.json()["status"], status)
        self.assertEqual(self.generate("ลดแป้ง").json().get("code"), "allergy_preferences_ambiguous")
        malformed = self.generate(["sesame"])
        self.assertEqual(malformed.status_code, 422)
        self.assertEqual(self.history_queries, [])
        self.provider.generate_content.assert_not_called()

    def seed_healthy(self):
        with self.sessions() as db:
            seed_allergen_graph(db)

    def test_healthy_kg_retries_derived_allergen_then_saves_only_accepted_recipe(self):
        self.seed_healthy()
        unsafe = deepcopy(SAFE)
        unsafe["adjusted_ingredients"].append("ทาฮินี (ไม่มีงา) 1 ช้อนโต๊ะ")
        for recipe_name, label in (("Thai Basil Pork", "แพ้งา"), ("Custom Recipe from Fridge", "งา")):
            with self.subTest(flow=recipe_name):
                self.provider.reset_mock()
                self.provider.generate_content.side_effect = [
                    SimpleNamespace(text=json.dumps(output, ensure_ascii=False)) for output in (unsafe, SAFE)]
                response = self.generate(label, extra_ingredients=("ทาฮินี (ไม่มีงา)",), recipe_name=recipe_name)
                self.assertEqual(response.json()["status"], "success", response.json())
                self.assertEqual(self.provider.generate_content.call_count, 2)
                prompt = self.provider.generate_content.call_args.kwargs["contents"]
                self.assertIn("Allergy violation:", prompt)
                self.assertIn("sesame", prompt)
                self.assertGreater(response.json()["data"]["history_id"], 0)
        histories = self.http.get("/api/history").json()["data"]
        self.assertEqual(len(histories), 2)
        self.assertTrue(all("ทาฮินี" not in " ".join(row["recipe_data"]["adjusted_ingredients"]) for row in histories))

    def test_persistent_violation_exhausts_three_attempts_without_history(self):
        self.seed_healthy()
        unsafe = deepcopy(SAFE)
        unsafe["adjusted_ingredients"].append("งาดำ 1 กรัม")
        self.provider.generate_content.return_value = SimpleNamespace(text=json.dumps(unsafe, ensure_ascii=False))
        response = self.generate("แพ้งา", extra_ingredients=("งาดำ",))
        self.assertEqual(response.json()["status"], "error")
        self.assertIn("งาดำ", response.json()["message"])
        self.assertEqual(self.provider.generate_content.call_count, 3)
        self.assertEqual(self.http.get("/api/history").json()["data"], [])

    def test_no_declared_allergy_generates_with_empty_kg(self):
        self.provider.generate_content.return_value = SimpleNamespace(text=json.dumps(SAFE, ensure_ascii=False))
        response = self.generate("ไม่มีอาการแพ้")
        self.assertEqual(response.json()["status"], "success", response.json())
        self.assertEqual(self.provider.generate_content.call_count, 1)


if __name__ == "__main__":
    unittest.main()
