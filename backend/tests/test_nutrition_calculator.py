# backend/tests/test_nutrition_calculator.py
import unittest
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, IngredientNutrition, IngredientNutritionAlias
from nutrition.calculator import compute_from_quantities, compute_recipe_nutrition
from nutrition.lookup import MacroValues


class ComputeRecipeNutritionTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(engine)
        self.shrimp = self._add("กุ้งก้ามกราม, สด", "กุ้ง", calories=90.0, protein_g=20.0, carbs_g=0.0, fat_g=1.0)
        self.garlic = self._add("กระเทียม, สด", "กระเทียม", calories=150.0, protein_g=6.0, carbs_g=33.0, fat_g=0.5)
        self.no_op_estimator = MagicMock()
        self.no_op_estimator.estimate.return_value = []

    def _add(self, full_name, alias, **macros):
        row = IngredientNutrition(ingredient_name=full_name, unit_basis="100g", source="INMU", **macros)
        self.db.add(row)
        self.db.flush()
        self.db.add(IngredientNutritionAlias(alias=alias, ingredient_nutrition_id=row.id))
        self.db.commit()
        return row

    def test_matched_and_resolved_ingredients_sum_correctly(self):
        result = compute_recipe_nutrition(self.db, ["กุ้ง 200 กรัม"], ["1. ผัดกุ้งกับกระเทียม"], servings=2, llm_estimator=self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 90.0)
        self.assertFalse(result.partially_estimated)

    def test_duplicate_ingredient_lines_are_both_summed(self):
        result = compute_recipe_nutrition(self.db, ["กระเทียม 50 กรัม", "กระเทียม 50 กรัม"], ["1. ทำอาหาร"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 150.0)

    def test_vague_quantity_on_a_real_ingredient_contributes_zero_and_flags(self):
        result = compute_recipe_nutrition(self.db, ["กระเทียมเล็กน้อย"], ["1. ทำอาหาร"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 0.0)
        self.assertTrue(result.partially_estimated)

    def test_zero_nutrition_constant_with_vague_quantity_does_not_flag(self):
        # (rev 3) Regression test for the exact bug found: this is the
        # MOST common phrasing in real Thai recipes for salt/water.
        result = compute_recipe_nutrition(self.db, ["เกลือเล็กน้อย"], ["1. ทำอาหาร"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 0.0)
        self.assertFalse(result.partially_estimated)

    def test_zero_nutrition_constant_with_a_real_quantity_also_works(self):
        result = compute_recipe_nutrition(self.db, ["เกลือ 5 กรัม"], ["1. ทำอาหาร"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 0.0)
        self.assertFalse(result.partially_estimated)

    def test_unmatched_name_with_global_unit_uses_llm_fallback(self):
        estimator = MagicMock()
        estimator.estimate.return_value = [MacroValues(calories=40.0, protein_g=1.0, carbs_g=8.0, fat_g=0.1)]
        result = compute_recipe_nutrition(self.db, ["ใบมะกรูด 10 กรัม"], ["1. ทำอาหาร"], servings=1, llm_estimator=estimator)
        estimator.estimate.assert_called_once_with(["ใบมะกรูด"])
        self.assertEqual(result.nutrition["calories"], 4.0)
        self.assertTrue(result.partially_estimated)

    def test_deep_fry_flags_even_when_fully_grounded(self):
        result = compute_recipe_nutrition(self.db, ["กุ้ง 200 กรัม"], ["1. ทอดกุ้งในน้ำมันร้อน"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertTrue(result.partially_estimated)
        self.assertTrue(any("deep-fry" in r for r in result.partially_estimated_reasons))

    def test_stir_fry_alone_does_not_trigger_deep_fry_flag(self):
        result = compute_recipe_nutrition(self.db, ["กุ้ง 200 กรัม"], ["1. ผัดกุ้งกับกระเทียม"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertFalse(result.partially_estimated)

    def test_matched_row_with_missing_macro_sums_known_macros_and_flags(self):
        pork = IngredientNutrition(
            ingredient_name="เนื้อหมู, สับ", unit_basis="100g", source="INMU", source_ref="F132",
            calories=None, protein_g=20.0, carbs_g=2.0, fat_g=10.0,
        )
        self.db.add(pork)
        self.db.flush()
        self.db.add(IngredientNutritionAlias(alias="หมูสับ", ingredient_nutrition_id=pork.id))
        self.db.commit()

        result = compute_recipe_nutrition(self.db, ["หมูสับ 200 กรัม"], ["1. ผัดหมู"], servings=1, llm_estimator=self.no_op_estimator)

        self.assertEqual(result.nutrition["protein_g"], 40.0)
        self.assertEqual(result.nutrition["carbs_g"], 4.0)
        self.assertEqual(result.nutrition["fat_g"], 20.0)
        self.assertEqual(result.nutrition["calories"], 0.0)
        self.assertTrue(result.partially_estimated)
        self.assertEqual(result.partially_estimated_reasons, ["missing calories in DB row F132: หมูสับ"])

    def test_llm_fallback_that_returned_nothing_is_not_worded_as_a_real_estimate(self):
        estimator = MagicMock()
        estimator.estimate.return_value = [MacroValues(None, None, None, None)]
        result = compute_recipe_nutrition(self.db, ["ใบมะกรูด 10 กรัม"], ["1. ทำอาหาร"], servings=1, llm_estimator=estimator)
        self.assertTrue(result.partially_estimated)
        self.assertEqual(result.partially_estimated_reasons, ["could not estimate composition (no LLM available): ใบมะกรูด"])

    def test_llm_fallback_real_estimate_keeps_llm_estimate_wording(self):
        estimator = MagicMock()
        estimator.estimate.return_value = [MacroValues(calories=40.0, protein_g=None, carbs_g=8.0, fat_g=0.1)]
        result = compute_recipe_nutrition(self.db, ["ใบมะกรูด 10 กรัม"], ["1. ทำอาหาร"], servings=1, llm_estimator=estimator)
        self.assertEqual(result.partially_estimated_reasons, ["LLM_ESTIMATE composition: ใบมะกรูด"])


class ComputeFromQuantitiesTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(engine)
        row = IngredientNutrition(ingredient_name="kale", unit_basis="100g", source="USDA", calories=49.0, protein_g=4.3, carbs_g=8.8, fat_g=0.9)
        self.db.add(row)
        self.db.flush()
        self.db.add(IngredientNutritionAlias(alias="kale", ingredient_nutrition_id=row.id))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_computes_from_pre_parsed_name_quantity_pairs(self):
        result = compute_from_quantities(self.db, [{"name": "kale", "quantity_g": 100.0}], servings=1)
        self.assertEqual(result["calories"], 49.0)

    def test_unmatched_name_raises_instead_of_silently_contributing_zero(self):
        with self.assertRaises(ValueError) as ctx:
            compute_from_quantities(self.db, [{"name": "unobtainium", "quantity_g": 100.0}], servings=1)
        self.assertIn("unobtainium", str(ctx.exception))

    def test_matched_row_with_missing_macro_raises_instead_of_silently_contributing_zero(self):
        row = IngredientNutrition(
            ingredient_name="incomplete row", unit_basis="100g", source="INMU", source_ref="X1",
            calories=100.0, protein_g=5.0, carbs_g=None, fat_g=1.0,
        )
        self.db.add(row)
        self.db.flush()
        self.db.add(IngredientNutritionAlias(alias="halfdata", ingredient_nutrition_id=row.id))
        self.db.commit()

        with self.assertRaises(ValueError) as ctx:
            compute_from_quantities(
                self.db,
                [{"name": "kale", "quantity_g": 100.0}, {"name": "halfdata", "quantity_g": 50.0}],
                servings=1,
            )
        self.assertIn("halfdata", str(ctx.exception))
        self.assertIn("carbs_g", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
