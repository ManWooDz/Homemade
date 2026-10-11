import unittest

from nutrition.units import GLOBAL_UNIT_GRAMS, resolve_grams, resolve_grams_detailed


class ResolveGramsTests(unittest.TestCase):
    def test_gram_unit_is_identity(self):
        self.assertEqual(resolve_grams(200.0, "กรัม", None), 200.0)

    def test_kilogram_converts_to_grams(self):
        self.assertEqual(resolve_grams(1.5, "กิโลกรัม", None), 1500.0)

    def test_khit_converts_to_grams(self):
        self.assertEqual(resolve_grams(2.0, "ขีด", None), 200.0)

    def test_milliliter_and_liter_treated_as_grams_1to1(self):
        self.assertEqual(resolve_grams(100.0, "มล.", None), 100.0)
        self.assertEqual(resolve_grams(1.0, "ลิตร", None), 1000.0)

    def test_unknown_unit_with_no_portion_data_is_unresolved(self):
        self.assertIsNone(resolve_grams(2.0, "ฟอง", None))

    def test_unknown_unit_resolved_via_ingredient_specific_portion_grams(self):
        self.assertEqual(resolve_grams(2.0, "ฟอง", {"ฟอง": 50.0}), 100.0)

    def test_portion_grams_present_but_missing_this_unit_is_unresolved(self):
        self.assertIsNone(resolve_grams(2.0, "ฟอง", {"ถ้วย": 240.0}))

    def test_measuring_cup_tablespoon_teaspoon_use_water_density(self):
        self.assertEqual(resolve_grams(1.0, "ถ้วยตวง", None), 240.0)
        self.assertEqual(resolve_grams(2.0, "ช้อนโต๊ะ", None), 30.0)
        self.assertEqual(resolve_grams(3.0, "ช้อนชา", None), 15.0)

    def test_ingredient_specific_portion_grams_still_beats_global_volume_unit(self):
        self.assertEqual(resolve_grams(2.0, "ช้อนโต๊ะ", {"ช้อนโต๊ะ": 12.5}), 25.0)

    def test_missing_quantity_is_unresolved(self):
        self.assertIsNone(resolve_grams(None, "กรัม", None))

    def test_missing_unit_is_unresolved(self):
        self.assertIsNone(resolve_grams(200.0, None, None))

    def test_direct_mass_metadata_and_numeric_wrapper_agree(self):
        for unit in ("กรัม", "ก.", "กิโลกรัม", "กก.", "ขีด", "มิลลิกรัม", "มก."):
            with self.subTest(unit=unit):
                result = resolve_grams_detailed(2, unit, None)
                self.assertEqual(result.grams, 2 * GLOBAL_UNIT_GRAMS[unit])
                self.assertEqual(result.grams, resolve_grams(2, unit, None))
                self.assertEqual(result.method, "direct_mass")
                self.assertIs(result.source_backed, True)

    def test_volume_fallback_is_explicitly_estimated(self):
        for unit in ("มล.", "มิลลิลิตร", "ลิตร", "ถ้วยตวง", "ช้อนโต๊ะ", "ช้อนชา"):
            with self.subTest(unit=unit):
                result = resolve_grams_detailed(2, unit, None)
                self.assertEqual(result.grams, resolve_grams(2, unit, None))
                self.assertEqual(result.method, "water_density_approximation")
                self.assertIs(result.source_backed, False)

    def test_uncited_portion_override_is_unknown_even_for_mass_unit(self):
        for unit in ("ฟอง", "ช้อนโต๊ะ", "กรัม"):
            with self.subTest(unit=unit):
                result = resolve_grams_detailed(2, unit, {unit: 12.5})
                self.assertEqual(result.grams, 25)
                self.assertEqual(result.method, "ingredient_portion")
                self.assertIsNone(result.source_backed)

    def test_zero_quantity_is_valid(self):
        self.assertEqual(resolve_grams(0, "กรัม", None), 0)
        self.assertEqual(resolve_grams(0, "ฟอง", {"ฟอง": 50}), 0)

    def test_validated_current_portion_factor_can_be_source_backed(self):
        result = resolve_grams_detailed(2, "ฟอง", {"ฟอง": 50}, verified_portion_grams={"ฟอง": 50})
        self.assertEqual((result.grams, result.method, result.source_backed), (100, "ingredient_portion", True))
        self.assertEqual(resolve_grams(2, "ฟอง", {"ฟอง": 50}), result.grams)
        self.assertIsNone(resolve_grams_detailed(2, "ฟอง", {"ฟอง": 50}).source_backed)

    def test_evidence_does_not_inject_units_or_override_current_factors(self):
        for evidence in ({"ฟอง": 55}, {"ถ้วย": 50}, {"ฟอง": True}, {"ฟอง": float("nan")}, [], "bad"):
            with self.subTest(evidence=evidence):
                result = resolve_grams_detailed(2, "ฟอง", {"ฟอง": 50}, verified_portion_grams=evidence)
                self.assertEqual(result.grams, 100)
                self.assertIsNone(result.source_backed)
        self.assertIsNone(resolve_grams_detailed(2, "ฟอง", None, verified_portion_grams={"ฟอง": 50}).grams)

    def test_qualified_portion_preserves_mass_override_and_invalid_rejection(self):
        result = resolve_grams_detailed(2, "กรัม", {"กรัม": 1}, verified_portion_grams={"กรัม": 1})
        self.assertEqual((result.grams, result.method, result.source_backed), (2, "ingredient_portion", True))
        self.assertIsNone(resolve_grams_detailed(2, "กรัม", {"กรัม": True}, verified_portion_grams={"กรัม": 1}).grams)

    def test_invalid_quantity_is_unresolved(self):
        for quantity in (True, False, "2", -1, float("nan"), float("inf"), -float("inf"), 10 ** 400):
            with self.subTest(quantity=quantity):
                result = resolve_grams_detailed(quantity, "กรัม", None)
                self.assertIsNone(result.grams)
                self.assertEqual(result.method, "unresolved")
                self.assertIsNone(result.source_backed)

    def test_invalid_override_never_falls_back_to_global(self):
        for factor in (None, True, False, "2", 0, -1, float("nan"), float("inf"), 10 ** 400):
            with self.subTest(factor=factor):
                self.assertIsNone(resolve_grams(2, "กรัม", {"กรัม": factor}))

    def test_overflow_is_unresolved(self):
        self.assertIsNone(resolve_grams(1e308, "กิโลกรัม", None))
        self.assertIsNone(resolve_grams(1e308, "ฟอง", {"ฟอง": 1e308}))

    def test_malformed_unit_or_portion_map_is_unresolved(self):
        for unit, portions in ((True, None), ([], None), ("", None), ("กรัม", []), ("กรัม", "bad")):
            with self.subTest(unit=unit, portions=portions):
                self.assertIsNone(resolve_grams(2, unit, portions))


if __name__ == "__main__":
    unittest.main()
