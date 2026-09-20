import unittest

from eval.metrics import (
    check_ingredient_hallucination,
    check_schema_and_constraints,
    summarize_run,
)


VALID_RECIPE = {
    "recipe_name": "Thai Basil Pork",
    "servings": 2,
    "adjusted_ingredients": ["หมูสับ 200 กรัม", "ใบกะเพรา 1 ถ้วย", "น้ำมัน 1 ช้อนโต๊ะ"],
    "diet_tags": ["Thai"],
    "nutrition": {"basis": "per_serving", "calories": 420, "protein_g": 28, "carbs_g": 18, "fat_g": 24},
    "instructions": ["1. ตั้งกระทะใส่น้ำมันแล้วผัดหมูให้สุก", "2. ใส่ใบกะเพรา"],
    "safety_warning": "ระวังความร้อนขณะประกอบอาหาร",
}


class CheckSchemaAndConstraintsTests(unittest.TestCase):
    def test_valid_recipe_passes(self):
        result = check_schema_and_constraints(VALID_RECIPE, ["หมูสับ"], {})
        self.assertTrue(result["valid"])
        self.assertIsNone(result["reason"])

    def test_malformed_recipe_fails_with_reason(self):
        result = check_schema_and_constraints({}, ["หมูสับ"], {})
        self.assertFalse(result["valid"])
        self.assertEqual(result["reason"], "Invalid recipe name")


class CheckIngredientHallucinationTests(unittest.TestCase):
    def test_recipe_using_only_provided_ingredients_and_staples_is_clean(self):
        result = check_ingredient_hallucination(VALID_RECIPE, ["หมูสับ", "ใบกะเพรา"])
        self.assertFalse(result["hallucinated"])
        self.assertEqual(result["unknown_ingredients"], [])

    def test_recipe_inventing_an_ingredient_is_flagged(self):
        recipe = dict(VALID_RECIPE, adjusted_ingredients=["กุ้งแม่น้ำ 300 กรัม"])
        result = check_ingredient_hallucination(recipe, ["หมูสับ"])
        self.assertTrue(result["hallucinated"])
        self.assertIn("กุ้งแม่น้ำ 300 กรัม", result["unknown_ingredients"])

    def test_pantry_staples_are_never_flagged(self):
        recipe = dict(VALID_RECIPE, adjusted_ingredients=["เกลือ 1 ช้อนชา", "น้ำปลา 1 ช้อนโต๊ะ"])
        result = check_ingredient_hallucination(recipe, [])
        self.assertFalse(result["hallucinated"])

    def test_water_staple_matches_despite_combining_mark_order_difference(self):
        # "นํ้าเปล่าเล็กน้อย" (nikhahit+mai-tho+sara-aa order) is the same
        # word as the staple "น้ำเปล่า" (mai-tho+sara-am) -- verified
        # 2026-09-21 that plain unicodedata.normalize("NFC", ...) does NOT
        # unify these (Thai SARA AM has no NFC decomposition mapping).
        recipe = dict(VALID_RECIPE, adjusted_ingredients=["นํ้าเปล่าเล็กน้อย 1 ถ้วย"])
        result = check_ingredient_hallucination(recipe, [])
        self.assertFalse(result["hallucinated"])
        self.assertEqual(result["unknown_ingredients"], [])


class SummarizeRunTests(unittest.TestCase):
    def test_summarize_computes_rates_and_latency(self):
        results = [
            {"valid": True, "hallucinated": False, "latency_seconds": 1.0},
            {"valid": False, "hallucinated": True, "latency_seconds": 3.0},
        ]
        summary = summarize_run(results)
        self.assertEqual(summary["n"], 2)
        self.assertEqual(summary["schema_validity_rate"], 0.5)
        self.assertEqual(summary["hallucination_rate"], 0.5)
        self.assertEqual(summary["mean_latency_seconds"], 2.0)

    def test_summarize_empty_results_does_not_divide_by_zero(self):
        summary = summarize_run([])
        self.assertEqual(summary["n"], 0)
        self.assertEqual(summary["schema_validity_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
