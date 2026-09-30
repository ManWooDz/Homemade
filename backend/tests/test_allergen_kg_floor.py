# backend/tests/test_allergen_kg_floor.py
import json
import os
import unittest

from allergen_kg.floor import (
    ALLERGEN_LABELS,
    ALLERGEN_MAP,
    ALLERGY_TRIGGER_KEYWORDS,
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


# Trigger coverage (2026-09-30): terms added so a user's stated allergy word maps
# to the allergen it refers to. Triggers only choose WHICH allergens are in play.
ADDED_TRIGGERS = {
    "shrimp": ["กะปิ", "อาหารทะเล"],
    "shellfish": ["หมึก", "squid", "octopus", "mussel", "ล็อบสเตอร์", "shellfish", "อาหารทะเล"],
    "fish": ["อาหารทะเล", "salmon", "tuna", "แซลมอน", "ทูน่า"],
    "milk": ["แลคโตส", "แล็กโทส", "lactose", "โยเกิร์ต", "yogurt", "whey"],
    "gluten": ["กลูเตน", "ข้าวสาลี", "บาร์เลย์", "ไรย์", "barley", "rye"],
    "soy": ["ซีอิ๊ว", "เต้าเจี้ยว", "tofu", "soya", "edamame"],
    "nut": ["พิสตาชิโอ", "pistachio", "แมคคาเดเมีย", "macadamia", "พีแคน", "pecan",
            "วอลนัท", "เฮเซลนัท", "เกาลัด", "เม็ดมะม่วง", "ถั่วเปลือกแข็ง", "tree nut"],
}
ADDED_ALLERGY_KEYWORDS = ["ไม่กิน", "ห้ามกิน", "กินไม่ได้", "allergic", "intolerant"]


class TriggerCoverageTests(unittest.TestCase):
    def test_every_added_trigger_flags_its_allergen(self):
        for key, terms in ADDED_TRIGGERS.items():
            for term in terms:
                with self.subTest(key=key, term=term):
                    flagged = detect_flagged_allergens({"allergy": "แพ้" + term})
                    self.assertIn(key, flagged)

    def test_every_added_trigger_is_registered_in_the_map(self):
        for key, terms in ADDED_TRIGGERS.items():
            for term in terms:
                with self.subTest(key=key, term=term):
                    self.assertIn(term, ALLERGEN_MAP[key]["triggers"])

    def test_seafood_flags_exactly_shrimp_shellfish_fish(self):
        self.assertEqual(
            detect_flagged_allergens({"allergy": "แพ้อาหารทะเล"}),
            ["shrimp", "shellfish", "fish"],
        )

    def test_thai_gluten_word_flags_exactly_gluten(self):
        self.assertEqual(detect_flagged_allergens({"allergy": "แพ้กลูเตน"}), ["gluten"])

    def test_term_without_allergy_keyword_flags_nothing(self):
        for text in ("กลูเตน", "ชอบกลูเตน", "อาหารทะเล", "ชอบอาหารทะเล", "lactose"):
            with self.subTest(text=text):
                self.assertEqual(detect_flagged_allergens({"allergy": text}), [])

    def test_new_allergy_keywords_activate_detection(self):
        cases = {
            "ไม่กินกุ้ง": "shrimp",
            "ห้ามกินนม": "milk",
            "กินไม่ได้ไข่": "egg",
            "allergic shrimp": "shrimp",
            "intolerant lactose": "milk",
        }
        for text, key in cases.items():
            with self.subTest(text=text):
                self.assertIn(key, detect_flagged_allergens({"allergy": text}))

    def test_added_allergy_keywords_are_registered(self):
        for kw in ADDED_ALLERGY_KEYWORDS:
            with self.subTest(kw=kw):
                self.assertIn(kw, ALLERGY_TRIGGER_KEYWORDS)

    def test_existing_behaviour_unchanged(self):
        self.assertEqual(detect_flagged_allergens({"allergy": "แพ้ถั่ว"}), ["peanut"])
        self.assertEqual(detect_flagged_allergens({"allergy": "แพ้กุ้ง"}), ["shrimp"])
        for value in ("", "none", "ไม่มี", "ไม่แพ้อาหาร", "no allergy"):
            self.assertEqual(detect_flagged_allergens({"allergy": value}), [])

    def test_added_terms_are_clean_strings(self):
        every = [t for terms in ADDED_TRIGGERS.values() for t in terms] + ADDED_ALLERGY_KEYWORDS
        for term in every:
            with self.subTest(term=term):
                self.assertIsInstance(term, str)
                self.assertTrue(term)
                self.assertEqual(term, term.strip())

    def test_no_duplicate_triggers(self):
        for key, mapping in ALLERGEN_MAP.items():
            with self.subTest(key=key):
                self.assertEqual(len(mapping["triggers"]), len(set(mapping["triggers"])))
        self.assertEqual(len(ALLERGY_TRIGGER_KEYWORDS), len(set(ALLERGY_TRIGGER_KEYWORDS)))

    def test_gluten_fixture_is_now_detected_end_to_end(self):
        path = os.path.join(os.path.dirname(__file__), os.pardir, "eval", "fixtures",
                            "generator_eval_cases.json")
        with open(path, encoding="utf-8") as fh:
            cases = json.load(fh)
        case = next(c for c in cases if c["case_id"] == "gluten_allergy_soy_sauce_known_gap")
        self.assertEqual(detect_flagged_allergens(case["user_prefs"]), ["gluten"])


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
