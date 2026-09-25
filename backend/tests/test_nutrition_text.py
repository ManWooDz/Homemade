import unittest

from nutrition.text import normalize_alias, normalize_thai


class NormalizeThaiTests(unittest.TestCase):
    def test_sara_am_variant_matches_canonical_form(self):
        self.assertEqual(normalize_thai("นํ้าเปล่า"), normalize_thai("น้ำเปล่า"))

    def test_plain_ascii_untouched(self):
        self.assertEqual(normalize_thai("shrimp"), "shrimp")


class NormalizeAliasTests(unittest.TestCase):
    def test_lowercases_and_strips(self):
        self.assertEqual(normalize_alias("  Shrimp  "), "shrimp")

    def test_thai_text_passed_through_normalize_thai(self):
        self.assertEqual(normalize_alias(" นํ้าเปล่า "), normalize_thai("น้ำเปล่า"))


if __name__ == "__main__":
    unittest.main()
