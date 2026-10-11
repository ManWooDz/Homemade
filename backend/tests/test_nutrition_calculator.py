# backend/tests/test_nutrition_calculator.py
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, IngredientNutrition, IngredientNutritionAlias
from nutrition.calculator import compute_from_quantities, compute_recipe_nutrition
from nutrition.lookup import MacroValues, NutritionMatch
from test_nutrition_evidence import synthetic_match


class ComputeRecipeNutritionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(self.engine)
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

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_matched_and_resolved_ingredients_sum_correctly(self):
        result = compute_recipe_nutrition(self.db, ["กุ้ง 200 กรัม"], ["1. ผัดกุ้งกับกระเทียม"], servings=2, llm_estimator=self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 90.0)
        self.assertTrue(result.partially_estimated)
        self.assertEqual(result.partially_estimated_reasons, ["DB identity/composition source unverified: กุ้ง"])

    def test_duplicate_ingredient_lines_are_both_summed(self):
        result = compute_recipe_nutrition(self.db, ["กระเทียม 50 กรัม", "กระเทียม 50 กรัม"], ["1. ทำอาหาร"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 150.0)

    def test_vague_quantity_on_a_real_ingredient_contributes_zero_and_flags(self):
        result = compute_recipe_nutrition(self.db, ["กระเทียมเล็กน้อย"], ["1. ทำอาหาร"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 0.0)
        self.assertTrue(result.partially_estimated)

    def test_zero_nutrition_constant_with_vague_quantity_flags_both_uncertainties(self):
        result = compute_recipe_nutrition(self.db, ["เกลือเล็กน้อย"], ["1. ทำอาหาร"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 0.0)
        self.assertTrue(result.partially_estimated)
        self.assertTrue(any("hardcoded zero" in r for r in result.partially_estimated_reasons))
        self.assertTrue(any("quantity not determined" in r for r in result.partially_estimated_reasons))
        self.no_op_estimator.estimate.assert_not_called()

    def test_zero_nutrition_constant_with_a_real_quantity_also_works(self):
        result = compute_recipe_nutrition(self.db, ["เกลือ 5 กรัม"], ["1. ทำอาหาร"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 0.0)
        self.assertTrue(result.partially_estimated)
        self.assertEqual(len(result.partially_estimated_reasons), 1)

    def test_unmatched_name_with_global_unit_uses_llm_fallback(self):
        estimator = MagicMock()
        estimator.estimate.return_value = [MacroValues(calories=40.0, protein_g=1.0, carbs_g=8.0, fat_g=0.1)]
        result = compute_recipe_nutrition(self.db, ["ใบมะกรูด 10 กรัม"], ["1. ทำอาหาร"], servings=1, llm_estimator=estimator)
        estimator.estimate.assert_called_once_with(["ใบมะกรูด"])
        self.assertEqual(result.nutrition["calories"], 4.0)
        self.assertTrue(result.partially_estimated)

    def test_deep_fry_flags_in_addition_to_row_uncertainty(self):
        result = compute_recipe_nutrition(self.db, ["กุ้ง 200 กรัม"], ["1. ทอดกุ้งในน้ำมันร้อน"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertTrue(result.partially_estimated)
        self.assertTrue(any("deep-fry" in r for r in result.partially_estimated_reasons))

    def test_stir_fry_alone_does_not_trigger_deep_fry_flag(self):
        result = compute_recipe_nutrition(self.db, ["กุ้ง 200 กรัม"], ["1. ผัดกุ้งกับกระเทียม"], servings=1, llm_estimator=self.no_op_estimator)
        self.assertFalse(any("deep-fry" in r for r in result.partially_estimated_reasons))

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
        self.assertIn("missing or invalid calories in DB row F132: หมูสับ", result.partially_estimated_reasons)

    def test_llm_fallback_that_returned_nothing_is_not_worded_as_a_real_estimate(self):
        estimator = MagicMock()
        estimator.estimate.return_value = [MacroValues(None, None, None, None)]
        result = compute_recipe_nutrition(self.db, ["ใบมะกรูด 10 กรัม"], ["1. ทำอาหาร"], servings=1, llm_estimator=estimator)
        self.assertTrue(result.partially_estimated)
        self.assertEqual(result.partially_estimated_reasons, ["could not estimate composition (no usable LLM result): ใบมะกรูด"])

    def test_llm_fallback_real_estimate_keeps_llm_estimate_wording(self):
        estimator = MagicMock()
        estimator.estimate.return_value = [MacroValues(calories=40.0, protein_g=None, carbs_g=8.0, fat_g=0.1)]
        result = compute_recipe_nutrition(self.db, ["ใบมะกรูด 10 กรัม"], ["1. ทำอาหาร"], servings=1, llm_estimator=estimator)
        self.assertEqual(result.partially_estimated_reasons, ["LLM_ESTIMATE composition: ใบมะกรูด"])

    def test_proxy_and_project_fill_methods_flag_without_losing_totals(self):
        for derivation, expected in (
            ({"proxy": "synthetic substitute"}, "proxy composition (synthetic substitute)"),
            ({"energy_kcal": "atwater"}, "project-filled energy_kcal (atwater)"),
            ({"carbs_g": "by_difference"}, "project-filled carbs_g (by_difference)"),
            ({"carbs_g": "by_difference_clamped"}, "project-filled carbs_g (by_difference_clamped)"),
        ):
            with self.subTest(derivation=derivation):
                self.shrimp.derivation = derivation
                self.db.commit()
                result = compute_recipe_nutrition(self.db, ["กุ้ง 100 กรัม"], [], 1, self.no_op_estimator)
                self.assertEqual(result.nutrition["calories"], 90)
                self.assertTrue(result.partially_estimated)
                self.assertTrue(any(expected in r for r in result.partially_estimated_reasons))
                self.no_op_estimator.estimate.assert_not_called()

    def test_source_ref_and_publisher_calculation_are_not_project_fill_proof(self):
        self.shrimp.source_ref = "synthetic-source"
        self.shrimp.derivation = {"publisher_method": "atwater"}
        self.db.commit()
        result = compute_recipe_nutrition(self.db, ["กุ้ง 100 กรัม"], [], 1, self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 90)
        self.assertTrue(result.partially_estimated)
        self.assertFalse(any("project-filled" in r or "proxy composition" in r for r in result.partially_estimated_reasons))

    def test_estimated_volume_and_uncited_portion_keep_numbers_and_method(self):
        for portions, method, calories in (
            (None, "water_density_approximation", 27),
            ({"ช้อนโต๊ะ": 12.5}, "ingredient_portion", 22.5),
        ):
            with self.subTest(portions=portions):
                self.shrimp.portion_grams = portions
                self.db.commit()
                result = compute_recipe_nutrition(self.db, ["กุ้ง 2 ช้อนโต๊ะ"], [], 1, self.no_op_estimator)
                self.assertEqual(result.nutrition["calories"], calories)
                self.assertTrue(any(method in r for r in result.partially_estimated_reasons))

    def test_incompatible_or_unknown_basis_is_skipped_without_llm(self):
        for basis in ("100ml", "unknown", None):
            with self.subTest(basis=basis):
                match = NutritionMatch(1, MacroValues(90, 20, 0, 1), "INMU", "synthetic", None, None, basis)
                with patch("nutrition.calculator.match_ingredient", return_value=match):
                    result = compute_recipe_nutrition(self.db, ["กุ้ง 100 กรัม"], [], 1, self.no_op_estimator)
                self.assertEqual(result.nutrition["calories"], 0)
                self.assertTrue(any("unsupported macro basis" in r for r in result.partially_estimated_reasons))
                self.no_op_estimator.estimate.assert_not_called()

    def test_invalid_macros_do_not_poison_valid_fields(self):
        for value in (True, "90", -1, float("nan"), float("inf"), 10 ** 400):
            with self.subTest(value=value):
                match = NutritionMatch(1, MacroValues(value, 20, 0, 1), "INMU", "synthetic", None, None, "100g")
                with patch("nutrition.calculator.match_ingredient", return_value=match):
                    result = compute_recipe_nutrition(self.db, ["กุ้ง 100 กรัม"], [], 1, self.no_op_estimator)
                self.assertEqual(result.nutrition["calories"], 0)
                self.assertEqual(result.nutrition["protein_g"], 20)
                self.assertTrue(any("missing or invalid calories" in r for r in result.partially_estimated_reasons))

    def test_numeric_zero_is_not_a_missing_macro(self):
        result = compute_recipe_nutrition(self.db, ["กุ้ง 0 กรัม"], [], 1, self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 0)
        self.assertFalse(any("missing or invalid" in r for r in result.partially_estimated_reasons))
        self.assertTrue(result.partially_estimated)

    def test_zero_constants_with_volume_or_unknown_unit_remain_partial(self):
        for raw, expected in (("น้ำเปล่า 1 ช้อนโต๊ะ", "water_density_approximation"), ("เกลือ 1 หยิบ", "quantity not determined")):
            with self.subTest(raw=raw):
                result = compute_recipe_nutrition(self.db, [raw], [], 1, self.no_op_estimator)
                self.assertEqual(result.nutrition["calories"], 0)
                self.assertTrue(any(expected in r for r in result.partially_estimated_reasons))
                self.no_op_estimator.estimate.assert_not_called()

    def test_invalid_portion_skips_contribution_without_llm(self):
        self.shrimp.portion_grams = {"กรัม": -1}
        self.db.commit()
        result = compute_recipe_nutrition(self.db, ["กุ้ง 100 กรัม"], [], 1, self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 0)
        self.assertTrue(result.partially_estimated)
        self.no_op_estimator.estimate.assert_not_called()

    def test_short_llm_result_flags_every_unestimated_ingredient(self):
        estimator = MagicMock()
        estimator.estimate.return_value = [MacroValues(40, 1, 8, 0)]
        result = compute_recipe_nutrition(self.db, ["ใบมะกรูด 10 กรัม", "ข่า 10 กรัม"], [], 1, estimator)
        self.assertEqual(result.nutrition["calories"], 4)
        self.assertIn("could not estimate composition (no usable LLM result): ข่า", result.partially_estimated_reasons)

    def test_empty_llm_result_cannot_claim_fully_grounded(self):
        result = compute_recipe_nutrition(self.db, ["ใบมะกรูด 10 กรัม"], [], 1, self.no_op_estimator)
        self.assertTrue(result.partially_estimated)
        self.assertEqual(result.nutrition["calories"], 0)

    def test_invalid_llm_macros_are_filtered(self):
        estimator = MagicMock()
        estimator.estimate.return_value = [MacroValues(float("nan"), 1, -8, True)]
        result = compute_recipe_nutrition(self.db, ["ใบมะกรูด 10 กรัม"], [], 1, estimator)
        self.assertEqual(result.nutrition["calories"], 0)
        self.assertEqual(result.nutrition["protein_g"], 0.1)
        self.assertEqual(result.nutrition["carbs_g"], 0)
        self.assertEqual(result.nutrition["fat_g"], 0)
        self.assertTrue(result.partially_estimated)

    def test_invalid_servings_raise_before_estimation(self):
        for servings in (True, 0, -1, float("nan"), float("inf")):
            with self.subTest(servings=servings), self.assertRaises(ValueError):
                compute_recipe_nutrition(self.db, ["ใบมะกรูด 10 กรัม"], [], servings, self.no_op_estimator)
        self.no_op_estimator.estimate.assert_not_called()

    def test_arithmetic_overflow_cannot_escape_as_infinite_nutrition(self):
        match = NutritionMatch(1, MacroValues(1e308, 20, 0, 1), "INMU", "synthetic", None, None, "100g")
        with patch("nutrition.calculator.match_ingredient", return_value=match), self.assertRaises(ValueError):
            compute_recipe_nutrition(self.db, ["กุ้ง 1000 กรัม"], [], 1, self.no_op_estimator)

    def test_per_serving_overflow_raises(self):
        with self.assertRaisesRegex(ValueError, "per-serving"):
            compute_recipe_nutrition(self.db, ["กุ้ง 100 กรัม"], [], 1e-308, self.no_op_estimator)

    def test_explicit_ascii_mass_units_use_existing_numeric_calculation(self):
        for raw in ("กุ้ง 200g", "กุ้ง 0.2kg", "กุ้ง 200000mg"):
            with self.subTest(raw=raw):
                result = compute_recipe_nutrition(self.db, [raw], [], 2, self.no_op_estimator)
                self.assertEqual(result.nutrition["calories"], 90)
                self.assertTrue(result.partially_estimated)
                self.no_op_estimator.estimate.assert_not_called()

    def test_synthetic_complete_evidence_and_mass_are_non_partial(self):
        match = synthetic_match()
        with patch("nutrition.calculator.match_ingredient", return_value=match):
            result = compute_recipe_nutrition(self.db, ["sample 200g"], [], 2, self.no_op_estimator)
        self.assertEqual(result.nutrition["calories"], 100)
        self.assertFalse(result.partially_estimated)
        self.assertEqual(result.partially_estimated_reasons, [])
        self.no_op_estimator.estimate.assert_not_called()

    def test_real_in_memory_lookup_preserves_synthetic_qualification(self):
        match = synthetic_match(alias="กุ้ง", full_name=self.shrimp.ingredient_name)
        self.shrimp.source_ref = match.source_ref
        for field in ("calories", "protein_g", "carbs_g", "fat_g"):
            setattr(self.shrimp, field, getattr(match.macros, field))
        self.shrimp.derivation = match.derivation
        self.db.commit()
        result = compute_recipe_nutrition(self.db, ["กุ้ง 100g"], [], 1, self.no_op_estimator)
        self.assertFalse(result.partially_estimated)
        self.assertEqual(result.nutrition["calories"], 100)

    def test_identity_composition_and_quantity_each_gate_qualification(self):
        for failure in ("identity", "macros", "quantity", "binding"):
            with self.subTest(failure=failure):
                match = synthetic_match()
                raw = "sample 100g"
                evidence = match.derivation["nutrition_evidence"]
                if failure == "identity":
                    evidence["identity"][0]["relation"] = "assumed"
                elif failure == "macros":
                    evidence["macros"][0]["origin"] = "project_imputed"
                elif failure == "quantity":
                    raw = "sample 1 ช้อนโต๊ะ"
                else:
                    match.source_ref = "changed"
                with patch("nutrition.calculator.match_ingredient", return_value=match):
                    result = compute_recipe_nutrition(self.db, [raw], [], 1, self.no_op_estimator)
                self.assertTrue(result.partially_estimated)
                self.assertGreater(result.nutrition["calories"], 0)

    def test_only_used_cited_portion_controls_gram_qualification(self):
        match = synthetic_match(portions={"ฟอง": 50, "ช้อนโต๊ะ": 12})
        evidence = match.derivation["nutrition_evidence"]
        evidence["portions"][1]["amount"] = 0
        with patch("nutrition.calculator.match_ingredient", return_value=match):
            cited = compute_recipe_nutrition(self.db, ["sample 2 ฟอง"], [], 1, self.no_op_estimator)
            uncited = compute_recipe_nutrition(self.db, ["sample 1 ช้อนโต๊ะ"], [], 1, self.no_op_estimator)
            mass = compute_recipe_nutrition(self.db, ["sample 100g"], [], 1, self.no_op_estimator)
        self.assertFalse(cited.partially_estimated)
        self.assertFalse(mass.partially_estimated)
        self.assertEqual(cited.nutrition["calories"], 100)
        self.assertTrue(uncited.partially_estimated)
        self.assertEqual(uncited.nutrition["calories"], 12)

    def test_estimate_markers_and_volume_basis_cannot_be_promoted(self):
        for markers, basis in (({"proxy": "synthetic substitute"}, "100g"),
                               ({"energy_kcal": "atwater"}, "100g"),
                               ({"carbs_g": "by_difference_clamped"}, "100g"), ({}, "100ml")):
            with self.subTest(markers=markers, basis=basis):
                match = synthetic_match(markers=markers, basis=basis)
                with patch("nutrition.calculator.match_ingredient", return_value=match):
                    result = compute_recipe_nutrition(self.db, ["sample 100g"], [], 1, self.no_op_estimator)
                self.assertTrue(result.partially_estimated)
                self.assertEqual(result.nutrition["calories"], 0 if basis == "100ml" else 100)

    def test_empty_zero_and_unparsed_inputs_do_not_waive_evidence(self):
        empty = compute_recipe_nutrition(self.db, [], [], 1, self.no_op_estimator)
        self.assertTrue(empty.partially_estimated)
        self.assertEqual(empty.nutrition["calories"], 0)
        match = synthetic_match()
        match.derivation = None
        with patch("nutrition.calculator.match_ingredient", return_value=match):
            zero = compute_recipe_nutrition(self.db, ["sample 0g"], [], 1, self.no_op_estimator)
        self.assertTrue(zero.partially_estimated)
        with patch("nutrition.calculator.match_ingredient", return_value=synthetic_match()):
            unparsed = compute_recipe_nutrition(self.db, ["sample 100g", "sample (raw) 100g"], [], 1, self.no_op_estimator)
        self.assertTrue(unparsed.partially_estimated)
        self.no_op_estimator.estimate.assert_not_called()

    def test_cooking_constants_and_mixed_recipes_still_partial(self):
        for raws, instructions in ((["sample 100g"], ["ทอด sample"]),
                                   (["sample 100g", "เกลือ 0g"], []),
                                   (["sample 100g", "other 100g"], [])):
            with self.subTest(raws=raws, instructions=instructions):
                verified = synthetic_match()
                legacy = synthetic_match(alias="other")
                legacy.derivation = None
                with patch("nutrition.calculator.match_ingredient", side_effect=lambda db, name: verified if name == "sample" else legacy):
                    result = compute_recipe_nutrition(self.db, raws, instructions, 1, self.no_op_estimator)
                self.assertTrue(result.partially_estimated)

    def test_publisher_published_calculation_can_qualify(self):
        match = synthetic_match()
        match.derivation["nutrition_evidence"]["macros"][0]["publisher_method"] = "source-published calculation"
        with patch("nutrition.calculator.match_ingredient", return_value=match):
            result = compute_recipe_nutrition(self.db, ["sample 100g"], [], 1, self.no_op_estimator)
        self.assertFalse(result.partially_estimated)

    def test_rejected_quantities_or_notes_skip_lookup_and_estimator(self):
        for raw in ("กุ้ง (สด) 200g", "กุ้ง 1,000 กรัม", "กุ้ง -5 กรัม", "กุ้ง 1 1/2g", "กุ้ง200g", "กุ้ง " + "9" * 400 + "g"):
            with self.subTest(raw=raw), patch("nutrition.calculator.match_ingredient") as lookup:
                result = compute_recipe_nutrition(self.db, [raw], [], 1, self.no_op_estimator)
                self.assertEqual(result.nutrition["calories"], 0)
                self.assertTrue(result.partially_estimated)
                lookup.assert_not_called()
                self.no_op_estimator.estimate.assert_not_called()


class ComputeFromQuantitiesTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(self.engine)
        self.row = IngredientNutrition(ingredient_name="kale", unit_basis="100g", source="USDA", calories=49.0, protein_g=4.3, carbs_g=8.8, fat_g=0.9)
        self.db.add(self.row)
        self.db.flush()
        self.db.add(IngredientNutritionAlias(alias="kale", ingredient_nutrition_id=self.row.id))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_computes_from_pre_parsed_name_quantity_pairs(self):
        result = compute_from_quantities(self.db, [{"name": "kale", "quantity_g": 100.0}], servings=1)
        self.assertEqual(result["calories"], 49.0)

    def test_unsupported_basis_raises_value_error_for_seed_fallback(self):
        self.row.unit_basis = "100ml"
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "unsupported macro basis"):
            compute_from_quantities(self.db, [{"name": "kale", "quantity_g": 100}], 1)

    def test_invalid_quantity_raises_even_for_zero_constant(self):
        for name in ("kale", "เกลือ"):
            for value in (True, "100", -1, float("nan"), float("inf")):
                with self.subTest(name=name, value=value), self.assertRaisesRegex(ValueError, "invalid gram quantity"):
                    compute_from_quantities(self.db, [{"name": name, "quantity_g": value}], 1)

    def test_invalid_macros_raise_instead_of_returning_poisoned_totals(self):
        match = NutritionMatch(1, MacroValues(float("inf"), 1, 1, 1), "USDA", "synthetic", None, None, "100g")
        with patch("nutrition.calculator.match_ingredient", return_value=match), self.assertRaisesRegex(ValueError, "calories"):
            compute_from_quantities(self.db, [{"name": "kale", "quantity_g": 100}], 1)

    def test_zero_quantity_and_zero_constants_remain_numeric_only(self):
        result = compute_from_quantities(self.db, [{"name": "kale", "quantity_g": 0}, {"name": "เกลือ", "quantity_g": 5}], 1)
        self.assertEqual(result["calories"], 0)

    def test_invalid_servings_raise(self):
        with self.assertRaises(ValueError):
            compute_from_quantities(self.db, [{"name": "kale", "quantity_g": 100}], 0)

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
