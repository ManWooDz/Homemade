# backend/tests/test_allergen_kg_floor.py
import unittest

from allergen_kg.floor import (
    ALLERGEN_LABELS,
    ALLERGEN_MAP,
    FLOOR_BLOCKS,
    detect_flagged_allergens,
)


class DetectFlaggedAllergensTests(unittest.TestCase):
    def test_no_allergy_values_flag_nothing(self):
        for prefs in ({}, {"allergy": ""}, {"allergy": "none"}, {"allergy": "ไม่มี"},
                      {"allergy": "ไม่แพ้อาหาร"}, {"allergy": "No allergy"}, {"allergy": None}):
            with self.subTest(prefs=prefs):
                self.assertEqual(detect_flagged_allergens(prefs), [])

    def test_requires_an_allergy_keyword(self):
        # Same as the old check_allergy: "กุ้ง" alone, without "แพ้"/"allergy", flags nothing.
        self.assertEqual(detect_flagged_allergens({"allergy": "กุ้ง"}), [])

    def test_thai_trigger(self):
        self.assertEqual(detect_flagged_allergens({"allergy": "แพ้กุ้ง"}), ["shrimp"])

    def test_english_mixed_case_trigger(self):
        self.assertEqual(detect_flagged_allergens({"allergy": "Allergic to Shrimp"}), ["shrimp"])

    def test_plain_string_prefs(self):
        self.assertEqual(detect_flagged_allergens("allergy: peanut"), ["peanut"])

    def test_two_allergies_in_one_sentence_keep_map_order(self):
        self.assertEqual(detect_flagged_allergens({"allergy": "แพ้นมและกุ้ง"}), ["shrimp", "milk"])

    def test_generic_tua_means_peanut_not_soy(self):
        self.assertEqual(detect_flagged_allergens({"allergy": "แพ้ถั่ว"}), ["peanut"])


class FloorConstantsTests(unittest.TestCase):
    def test_floor_blocks_mirror_allergen_map_blocks(self):
        self.assertEqual(FLOOR_BLOCKS, {k: v["blocks"] for k, v in ALLERGEN_MAP.items()})

    def test_every_key_has_a_display_label(self):
        self.assertEqual(set(ALLERGEN_LABELS), set(ALLERGEN_MAP))

    def test_main_still_exports_allergen_map(self):
        import main
        self.assertIs(main.ALLERGEN_MAP, ALLERGEN_MAP)


if __name__ == "__main__":
    unittest.main()
