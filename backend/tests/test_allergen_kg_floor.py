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


# The real frontend (CreateRecipe.jsx / CustomCookingPage.jsx) sends the user's
# allergies under the PLURAL key "allergies" as a comma-joined string of pill labels.
ALL_ALLERGY_PILLS = ["แพ้ถั่ว", "แพ้นม / ผลิตภัณฑ์จากนม", "แพ้อาหารทะเล",
                     "แพ้แป้งสาลี / Gluten", "แพ้ปลา", "แพ้ถั่วเหลือง", "แพ้งา"]


def frontend_prefs(allergies):
    return {"taste": "", "allergies": allergies, "equipment": "", "extra": ""}


class FrontendShapedAllergiesKeyTests(unittest.TestCase):
    def test_peanut_pill(self):
        self.assertIn("peanut", detect_flagged_allergens(frontend_prefs("แพ้ถั่ว")))

    def test_milk_pill(self):
        self.assertIn("milk", detect_flagged_allergens(frontend_prefs("แพ้นม / ผลิตภัณฑ์จากนม")))

    def test_egg_pill(self):
        self.assertIn("egg", detect_flagged_allergens(frontend_prefs("แพ้ไข่")))

    def test_seafood_pill_flags_exactly_shrimp_shellfish_fish(self):
        self.assertEqual(detect_flagged_allergens(frontend_prefs("แพ้อาหารทะเล")),
                         ["shrimp", "shellfish", "fish"])

    def test_gluten_pill(self):
        self.assertIn("gluten", detect_flagged_allergens(frontend_prefs("แพ้แป้งสาลี / Gluten")))

    def test_fish_pill(self):
        self.assertIn("fish", detect_flagged_allergens(frontend_prefs("แพ้ปลา")))

    def test_soy_pill(self):
        self.assertIn("soy", detect_flagged_allergens(frontend_prefs("แพ้ถั่วเหลือง")))

    def test_sesame_pill_flags_nothing_known_scope_limit_no_sesame_key(self):
        # KNOWN SCOPE LIMIT: ALLERGEN_MAP has no sesame key, so the "แพ้งา" pill maps to nothing.
        self.assertEqual(detect_flagged_allergens(frontend_prefs("แพ้งา")), [])

    def test_none_pill_and_empty_flag_nothing(self):
        for text in ("ไม่มีข้อจำกัด", ""):
            with self.subTest(text=text):
                self.assertEqual(detect_flagged_allergens(frontend_prefs(text)), [])

    def test_diet_labels_only_flag_nothing(self):
        self.assertEqual(detect_flagged_allergens(frontend_prefs("ทาน Vegan, ฮาลาล")), [])

    def test_all_pills_joined_flag_every_key_in_map_order(self):
        joined = ", ".join(ALL_ALLERGY_PILLS)
        lowered = joined.lower()
        expected = [key for key, mapping in ALLERGEN_MAP.items()
                    if any(t in lowered for t in mapping["triggers"])]
        # Hand-checked: none of these 7 pills mentions egg (separate "แพ้ไข่" pill) or tree
        # nuts, and sesame has no key, so those add nothing; the rest follow ALLERGEN_MAP order.
        self.assertEqual(expected, [k for k in ALLERGEN_MAP if k not in ("egg", "nut")])
        self.assertEqual(detect_flagged_allergens(frontend_prefs(joined)), expected)


class BothAllergyKeysTests(unittest.TestCase):
    def test_both_keys_combine_in_map_order(self):
        self.assertEqual(
            detect_flagged_allergens({"allergy": "แพ้กุ้ง", "allergies": "แพ้นม"}),
            ["shrimp", "milk"])

    def test_both_keys_combine_regardless_of_key_order(self):
        self.assertEqual(
            detect_flagged_allergens({"allergies": "แพ้นม", "allergy": "แพ้กุ้ง"}),
            ["shrimp", "milk"])

    def test_allergy_only_and_allergies_only_are_identical_for_gated_text(self):
        # Text that carries an allergy keyword (or a none-sentinel) behaves the same under
        # either key. Bare terms ("กุ้ง") intentionally differ: see AllergiesKeyIsUngatedTests.
        for text in ("แพ้กุ้ง", "แพ้ถั่ว", "Allergic to Shrimp", "ไม่มี"):
            with self.subTest(text=text):
                self.assertEqual(detect_flagged_allergens({"allergy": text}),
                                 detect_flagged_allergens({"allergies": text}))

    def test_none_sentinel_in_one_key_does_not_hide_the_other(self):
        self.assertEqual(
            detect_flagged_allergens({"allergy": "ไม่มี", "allergies": "แพ้กุ้ง"}), ["shrimp"])

    def test_non_str_values_never_raise(self):
        for bad in (None, 5, ["แพ้กุ้ง"], {"a": 1}, 0.5, False):
            for key in ("allergy", "allergies"):
                with self.subTest(key=key, bad=bad):
                    self.assertIsInstance(detect_flagged_allergens({key: bad}), list)
        self.assertEqual(detect_flagged_allergens({"allergy": None, "allergies": None}), [])
        self.assertEqual(detect_flagged_allergens({"allergy": 5, "allergies": 5}), [])


# CustomCookingPage.jsx pill labels: NO "แพ้" prefix. Free-text "other" entries are raw too.
# The plural "allergies" key IS an allergy list by definition, so it bypasses the keyword
# gate; the singular "allergy" key and plain-string prefs keep the gate.
CUSTOM_COOKING_PILLS = {
    "กุ้ง/อาหารทะเล": ["shrimp", "shellfish", "fish"],
    "ถั่ว": ["peanut"],
    "นม/ผลิตภัณฑ์จากนม": ["milk"],
    "ไข่": ["egg"],
    "แป้งสาลี/กลูเตน": ["gluten"],
    # The generic trigger "ถั่ว" is a substring of "ถั่วเหลือง", so peanut is flagged as well
    # as soy. Over-flagging is the safe direction (extra block terms), documented not fixed.
    "ถั่วเหลือง": ["peanut", "soy"],
    # KNOWN SCOPE LIMIT: ALLERGEN_MAP has no sesame key, so "งา" maps to nothing.
    "งา": [],
}


class AllergiesKeyIsUngatedTests(unittest.TestCase):
    def test_every_custom_cooking_pill_individually(self):
        for label, expected in CUSTOM_COOKING_PILLS.items():
            with self.subTest(label=label):
                self.assertEqual(detect_flagged_allergens(frontend_prefs(label)), expected)

    def test_free_text_bare_terms(self):
        cases = {"กุ้ง": ["shrimp"], "shrimp": ["shrimp"], "ปู": ["shellfish"]}
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(detect_flagged_allergens(frontend_prefs(text)), expected)

    def test_none_sentinels_and_empty_flag_nothing(self):
        for text in ("ไม่มีข้อจำกัด", "ไม่มีอาการแพ้", "ไม่มี", "None", "  ", ""):
            with self.subTest(text=text):
                self.assertEqual(detect_flagged_allergens(frontend_prefs(text)), [])

    def test_diet_words_only_flag_nothing(self):
        self.assertEqual(detect_flagged_allergens(frontend_prefs("ทาน Vegan, ฮาลาล")), [])

    def test_bare_term_in_allergies_combines_with_gated_singular_key(self):
        self.assertEqual(
            detect_flagged_allergens({"allergy": "แพ้นม", "allergies": "กุ้ง"}), ["shrimp", "milk"])

    def test_singular_key_keeps_the_keyword_gate(self):
        self.assertEqual(detect_flagged_allergens({"allergy": "ชอบกุ้ง"}), [])
        self.assertEqual(detect_flagged_allergens({"allergy": "กุ้ง"}), [])
        self.assertEqual(detect_flagged_allergens({"allergy": "ถั่ว"}), [])

    def test_singular_key_none_sentinels_flag_nothing(self):
        for text in ("ไม่มีข้อจำกัด", "ไม่มีอาการแพ้"):
            with self.subTest(text=text):
                self.assertEqual(detect_flagged_allergens({"allergy": text}), [])

    def test_plain_string_prefs_keep_the_keyword_gate(self):
        self.assertEqual(detect_flagged_allergens("กุ้ง"), [])
        self.assertEqual(detect_flagged_allergens("ชอบกุ้ง"), [])
        self.assertEqual(detect_flagged_allergens("allergy: peanut"), ["peanut"])
        self.assertEqual(detect_flagged_allergens("ไม่มีอาการแพ้"), [])

    def test_no_allergy_values_include_new_sentinels(self):
        from allergen_kg.floor import NO_ALLERGY_VALUES
        for value in ("ไม่มีข้อจำกัด", "ไม่มีอาการแพ้"):
            self.assertIn(value, NO_ALLERGY_VALUES)


class CheckAllergyLegacyPathAllergiesKeyTests(unittest.TestCase):
    def test_allergies_key_now_blocks_on_legacy_path(self):
        from main import check_allergy
        for ingredient in ("กะปิ 1 ช้อนชา", "กุ้งสด 200 กรัม"):
            with self.subTest(ingredient=ingredient):
                ok, reason = check_allergy({"adjusted_ingredients": [ingredient]},
                                           {"allergies": "แพ้กุ้ง"})
                self.assertFalse(ok)
                self.assertTrue(reason.startswith("Allergy violation:"), reason)


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
