# backend/tests/test_allergen_kg_endpoint.py
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from allergen_kg.fixtures import add_edges, make_memory_db
from main import (
    GenerateRecipeTextRequest,
    generate_recipe_text,
    resolve_blocks_for_request,
    run_generation_with_validation,
)
from nutrition.calculator import NutritionResult

_STUB_NUTRITION = NutritionResult(
    nutrition={"basis": "per_serving", "calories": 1.0, "protein_g": 1.0, "carbs_g": 1.0, "fat_g": 1.0},
    partially_estimated=False,
    partially_estimated_reasons=[],
)

SAFE = {
    "recipe_name": "Test Dish",
    "servings": 2,
    "adjusted_ingredients": ["หมูสับ 200 กรัม", "น้ำมัน 1 ช้อนโต๊ะ"],
    "diet_tags": ["Thai"],
    "nutrition": {"basis": "per_serving", "calories": 400, "protein_g": 20, "carbs_g": 10, "fat_g": 20},
    "instructions": ["1. ตั้งกระทะใส่น้ำมันแล้วผัดหมู"],
    "safety_warning": "ระวังความร้อน",
}


def with_ingredient(name):
    r = deepcopy(SAFE)
    r["adjusted_ingredients"] = [f"{name} 1 ช้อนโต๊ะ", "น้ำมัน 1 ช้อนโต๊ะ"]
    return r


def request(allergy):
    return GenerateRecipeTextRequest(
        recipe={"name": "Custom"},
        ingredients=[{"id": 1, "name": "หมูสับ"}],
        preferences={"allergy": allergy, "taste": "", "equipment": "", "extra": ""},
    )


class ResolveForRequestTests(unittest.TestCase):
    def test_no_allergy_never_opens_a_session(self):
        with patch("main.SessionLocal") as session_factory:
            self.assertEqual(resolve_blocks_for_request({"allergy": ""}), {})
        session_factory.assert_not_called()

    def test_database_url_unset_gives_floor_only(self):
        with patch("main.SessionLocal", None):
            resolved = resolve_blocks_for_request({"allergy": "แพ้กุ้ง"})
        self.assertEqual(resolved["shrimp"].graph_status, "unavailable")
        self.assertIn("กุ้ง", resolved["shrimp"].terms)

    def test_session_failure_gives_floor_only(self):
        def broken():
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        with patch("main.SessionLocal", broken):
            resolved = resolve_blocks_for_request({"allergy": "แพ้กุ้ง"})
        self.assertEqual(resolved["shrimp"].graph_status, "unavailable")

    def test_uses_seeded_graph(self):
        db = make_memory_db()
        add_edges(db, [("alpha", "allergen:shrimp"), ("beta", "alpha")])
        with patch("main.SessionLocal", lambda: db):
            resolved = resolve_blocks_for_request({"allergy": "แพ้กุ้ง"})
        self.assertEqual(resolved["shrimp"].graph_status, "ok")
        self.assertIn("beta", resolved["shrimp"].terms)


class RunGenerationTests(unittest.TestCase):
    def test_returns_first_passing_recipe_and_logs_attempts(self):
        blocks = {}
        outputs = [with_ingredient("กุ้ง"), deepcopy(SAFE)]
        feedbacks = []

        def fake(ingredients, user_prefs, base_recipe, feedback=None):
            feedbacks.append(feedback)
            return outputs.pop(0)

        final, log = run_generation_with_validation(
            fake, ["หมูสับ"], ["หมูสับ"], {"allergy": "แพ้กุ้ง"}, {"name": "x"}, blocks)
        self.assertEqual(final["recipe_name"], "Test Dish")
        self.assertEqual([e["status"] for e in log], ["fail", "pass"])
        self.assertEqual(feedbacks[0], None)
        self.assertTrue(feedbacks[1].startswith("Allergy violation:"))

    def test_exhaustion_returns_none(self):
        final, log = run_generation_with_validation(
            lambda *a, **k: with_ingredient("กุ้ง"), ["หมูสับ"], ["หมูสับ"],
            {"allergy": "แพ้กุ้ง"}, {"name": "x"}, {})
        self.assertIsNone(final)
        self.assertEqual(len(log), 3)

    def test_generator_error_short_circuits(self):
        final, log = run_generation_with_validation(
            lambda *a, **k: {"error": "no key"}, [], [], {}, {"name": "x"}, {})
        self.assertEqual(final, {"error": "no key"})
        self.assertEqual(log, [{"attempt": 1, "status": "error", "reason": "no key"}])


class EndpointTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = patch("main.compute_recipe_nutrition", return_value=_STUB_NUTRITION)
        patcher.start()
        self.addCleanup(patcher.stop)

        history_patcher = patch("main.save_generate_history", return_value=101)
        history_patcher.start()
        self.addCleanup(history_patcher.stop)

    async def test_endpoint_feeds_kg_chain_reason_back_to_generator(self):
        db = make_memory_db()
        add_edges(db, [("alpha", "allergen:shrimp"), ("beta", "alpha")])
        outputs = [with_ingredient("beta"), deepcopy(SAFE)]
        feedbacks = []

        def fake(ingredients, user_prefs, base_recipe, feedback=None):
            feedbacks.append(feedback)
            return outputs.pop(0)

        with patch("main.SessionLocal", lambda: db), patch("main.call_agentic_llm", side_effect=fake):
            response = await generate_recipe_text(request("แพ้กุ้ง"), current_user=SimpleNamespace(id=7), db=object())

        self.assertEqual(response["status"], "success")
        self.assertEqual(feedbacks[1], "Allergy violation: 'beta' → alpha → กุ้ง (ผู้ใช้แพ้ shrimp)")

    async def test_endpoint_still_blocks_floor_when_db_unset(self):
        outputs = [with_ingredient("กุ้ง"), deepcopy(SAFE)]
        feedbacks = []

        def fake(ingredients, user_prefs, base_recipe, feedback=None):
            feedbacks.append(feedback)
            return outputs.pop(0)

        with patch("main.SessionLocal", None), patch("main.call_agentic_llm", side_effect=fake):
            response = await generate_recipe_text(request("แพ้กุ้ง"), current_user=SimpleNamespace(id=7), db=object())

        self.assertEqual(response["status"], "success")
        self.assertEqual(feedbacks[1], "Allergy violation: พบ 'กุ้ง' ในสูตร (ผู้ใช้แพ้ shrimp)")


if __name__ == "__main__":
    unittest.main()
