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

    def test_trailing_parenthetical_identity_note_abstains(self):
        result = parse_ingredient_string("กุ้ง 200 กรัม (แกะเปลือก)")
        self.assertEqual(result.name, "กุ้ง 200 กรัม (แกะเปลือก)")
        self.assertIsNone(result.quantity)
        self.assertEqual(result.parse_status, "unparsed")

    def test_vague_word_inside_note_does_not_get_silently_removed(self):
        result = parse_ingredient_string("น้ำปลา 1 ช้อนโต๊ะ (ปรุงรสตามชอบ)")
        self.assertIn("(ปรุงรสตามชอบ)", result.name)
        self.assertIsNone(result.quantity)
        self.assertEqual(result.parse_status, "unparsed")

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

    def test_parenthetical_composition_before_quantity_is_retained(self):
        result = parse_ingredient_string("กะปิเจ (ทำจากถั่วเหลืองหรือธัญพืช) 1 ช้อนโต๊ะ")
        self.assertIn("ทำจากถั่วเหลืองหรือธัญพืช", result.name)
        self.assertIsNone(result.quantity)
        self.assertIsNone(result.unit)
        self.assertEqual(result.parse_status, "unparsed")

    def test_lowercase_mass_suffixes_canonicalize_with_or_without_unit_space(self):
        for suffix, expected in (("g", "กรัม"), ("kg", "กิโลกรัม"), ("mg", "มิลลิกรัม")):
            for gap in ("", " "):
                with self.subTest(suffix=suffix, gap=gap):
                    result = parse_ingredient_string(f"sample 0.5{gap}{suffix}")
                    self.assertEqual((result.name, result.quantity, result.unit, result.parse_status), ("sample", 0.5, expected, "ok"))

    def test_fraction_and_zero_remain_valid(self):
        for token, expected in (("1/2", 0.5), ("0/2", 0), ("0", 0)):
            with self.subTest(token=token):
                result = parse_ingredient_string(f"sample {token}g")
                self.assertEqual(result.quantity, expected)
                self.assertEqual(result.parse_status, "ok")

    def test_digits_in_product_name_are_preserved(self):
        result = parse_ingredient_string("sample B12 200g")
        self.assertEqual(result.name, "sample B12")
        self.assertEqual(result.quantity, 200)

    def test_compact_name_number_has_no_explicit_boundary(self):
        for raw in ("sample200g", "กุ้ง200กรัม"):
            with self.subTest(raw=raw):
                self.assertEqual(parse_ingredient_string(raw).parse_status, "unparsed")

    def test_ambiguous_or_malformed_amount_is_never_salvaged(self):
        for token in ("1,000", "1,5", "1, 000", "-5", "+5", "- 5", "−5", "1 1/2", "1 / 2", "1. 5", "1e3", "1e 3", "1e+ 3", "1-2", "1 – 2", "1/0", "1.5/2"):
            with self.subTest(token=token):
                result = parse_ingredient_string(f"sample {token}g")
                self.assertEqual(result.parse_status, "unparsed")
                self.assertIsNone(result.quantity)
                self.assertIsNone(result.unit)

    def test_nonfinite_numerator_or_denominator_is_rejected(self):
        huge = "9" * 400
        for token in (huge, huge + "/2", "1/" + huge):
            with self.subTest(token=token):
                self.assertEqual(parse_ingredient_string(f"sample {token}g").parse_status, "unparsed")

    def test_parentheses_are_preserved_even_when_unbalanced_or_nested(self):
        for raw in ("sample (raw 200g", "sample ) 200g", "sample ((raw)) 200g", "sample 200g (note)"):
            with self.subTest(raw=raw):
                result = parse_ingredient_string("  " + raw + "  ")
                self.assertEqual(result.name, raw)
                self.assertEqual(result.raw, "  " + raw + "  ")
                self.assertEqual(result.parse_status, "unparsed")

    def test_unrequested_ascii_units_stay_unparsed(self):
        for unit in ("G", "KG", "Mg", "ml", "lb", "grams"):
            with self.subTest(unit=unit):
                self.assertEqual(parse_ingredient_string(f"sample 200{unit}").parse_status, "unparsed")


if __name__ == "__main__":
    unittest.main()
