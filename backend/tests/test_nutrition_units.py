import unittest

from nutrition.units import resolve_grams


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

    def test_missing_quantity_is_unresolved(self):
        self.assertIsNone(resolve_grams(None, "กรัม", None))

    def test_missing_unit_is_unresolved(self):
        self.assertIsNone(resolve_grams(200.0, None, None))


if __name__ == "__main__":
    unittest.main()
