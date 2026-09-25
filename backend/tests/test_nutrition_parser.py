import unittest

from nutrition.parser import parse_ingredient_string


class ParseIngredientStringTests(unittest.TestCase):
    def test_grams_with_space(self):
        result = parse_ingredient_string("กุ้ง 200 กรัม")
        self.assertEqual(result.name, "กุ้ง")
        self.assertEqual(result.quantity, 200.0)
        self.assertEqual(result.unit, "กรัม")
        self.assertEqual(result.parse_status, "ok")

    def test_tablespoon_unit(self):
        result = parse_ingredient_string("น้ำปลา 2 ช้อนโต๊ะ")
        self.assertEqual(result.quantity, 2.0)
        self.assertEqual(result.unit, "ช้อนโต๊ะ")

    def test_milliliter_unit(self):
        result = parse_ingredient_string("น้ำปลา 30 มล.")
        self.assertEqual(result.quantity, 30.0)
        self.assertEqual(result.unit, "มล.")

    def test_decimal_quantity(self):
        self.assertEqual(parse_ingredient_string("น้ำมัน 1.5 ช้อนโต๊ะ").quantity, 1.5)

    def test_fraction_quantity(self):
        result = parse_ingredient_string("มะนาว 1/2 ลูก")
        self.assertEqual(result.quantity, 0.5)
        self.assertEqual(result.unit, "ลูก")
        self.assertEqual(result.parse_status, "ok")

    def test_trailing_parenthetical_note_does_not_break_parsing(self):
        result = parse_ingredient_string("กุ้ง 200 กรัม (แกะเปลือก)")
        self.assertEqual(result.name, "กุ้ง")
        self.assertEqual(result.quantity, 200.0)
        self.assertEqual(result.parse_status, "ok")

    def test_vague_word_only_inside_trailing_note_does_not_mark_unparsed(self):
        result = parse_ingredient_string("น้ำปลา 1 ช้อนโต๊ะ (ปรุงรสตามชอบ)")
        self.assertEqual(result.quantity, 1.0)
        self.assertEqual(result.parse_status, "ok")

    def test_vague_quantity_word_is_unparsed(self):
        result = parse_ingredient_string("เกลือเล็กน้อย")
        self.assertEqual(result.parse_status, "unparsed")
        self.assertIsNone(result.quantity)
        self.assertEqual(result.name, "เกลือ")

    def test_taste_to_preference_is_unparsed(self):
        self.assertEqual(parse_ingredient_string("พริกไทยตามชอบ").parse_status, "unparsed")

    def test_numeric_range_is_unparsed_not_averaged(self):
        result = parse_ingredient_string("พริก 1-2 เม็ด")
        self.assertEqual(result.parse_status, "unparsed")
        self.assertIsNone(result.quantity)

    def test_no_quantity_at_all_is_unparsed(self):
        result = parse_ingredient_string("ใบมะกรูด")
        self.assertEqual(result.parse_status, "unparsed")
        self.assertEqual(result.name, "ใบมะกรูด")

    def test_raw_is_preserved_verbatim(self):
        self.assertEqual(parse_ingredient_string("  กุ้ง 200 กรัม  ").raw, "  กุ้ง 200 กรัม  ")

    def test_exact_prompt_staple_words_parse_cleanly(self):
        # (rev 3) These 7 exact words are what main.py's own prompt (rule
        # 6) instructs the LLM to use for pantry staples -- verified
        # directly against the real prompt text and VALID_RECIPE fixture
        # in test_generate_handler.py ("น้ำมัน 1 ช้อนโต๊ะ").
        for raw, expected_name in [
            ("เกลือ 1 ช้อนชา", "เกลือ"), ("พริกไทย 1 ช้อนชา", "พริกไทย"),
            ("น้ำมัน 1 ช้อนโต๊ะ", "น้ำมัน"), ("น้ำปลา 1 ช้อนโต๊ะ", "น้ำปลา"),
            ("ซีอิ๊ว 1 ช้อนโต๊ะ", "ซีอิ๊ว"), ("น้ำตาล 1 ช้อนชา", "น้ำตาล"),
            ("น้ำเปล่า 200 มล.", "น้ำเปล่า"),
        ]:
            with self.subTest(raw=raw):
                result = parse_ingredient_string(raw)
                self.assertEqual(result.name, expected_name)
                self.assertEqual(result.parse_status, "ok")

    def test_parenthetical_note_before_quantity_does_not_pollute_name(self):
        # (Step 5, real Gemini output, case
        # shrimp_allergy_should_avoid_shrimp_and_shrimp_paste, 2026-09-25)
        # Unlike the trailing-note tests above, this note sits BEFORE the
        # quantity/unit -- the original _TRAILING_NOTE_RE (anchored to the
        # end of the string) doesn't strip it, so the name previously came
        # out as "กะปิเจ (ทำจากถั่วเหลืองหรือธัญพืช" (a broken, unclosed
        # paren fragment folded into the name by the greedy-backtracking
        # name group) instead of the clean ingredient name.
        result = parse_ingredient_string("กะปิเจ (ทำจากถั่วเหลืองหรือธัญพืช) 1 ช้อนโต๊ะ")
        self.assertEqual(result.name, "กะปิเจ")
        self.assertEqual(result.quantity, 1.0)
        self.assertEqual(result.unit, "ช้อนโต๊ะ")
        self.assertEqual(result.parse_status, "ok")


if __name__ == "__main__":
    unittest.main()
