import unittest

from finetune.thai_text import dish_families_overlap, extract_ingredient_name


class ExtractIngredientNameTests(unittest.TestCase):
    def test_strips_trailing_quantity_and_unit(self):
        self.assertEqual(extract_ingredient_name("กุ้งนาง 4 ตัว"), "กุ้งนาง")

    def test_strips_parenthetical_note(self):
        self.assertEqual(
            extract_ingredient_name("กะเทียม 5 กลีบ (ขนาดกลาง)"), "กะเทียม"
        )

    def test_no_digit_present_keeps_whole_string(self):
        self.assertEqual(extract_ingredient_name("พริกไทยป่นพอควร"), "พริกไทยป่นพอควร")

    def test_strips_leading_bullet_and_whitespace(self):
        self.assertEqual(extract_ingredient_name("- น้ำปลา 2 ช้อนโต๊ะ"), "น้ำปลา")


class DishFamiliesOverlapTests(unittest.TestCase):
    KEYWORD_PAIRS = [("ส้มตำ", "Som Tam"), ("ปลาหมึก", "Squid"), ("ต้มยำ", "Tom Yum")]

    def test_matching_keyword_pair_in_either_name_order_is_overlap(self):
        self.assertTrue(
            dish_families_overlap("ส้มตำแตงร้าน", "Som Tam", self.KEYWORD_PAIRS)
        )

    def test_matches_regardless_of_which_argument_is_which_language(self):
        self.assertTrue(
            dish_families_overlap("Som Tam", "ส้มตำแตงร้าน", self.KEYWORD_PAIRS)
        )

    def test_no_shared_keyword_pair_is_not_overlap(self):
        self.assertFalse(
            dish_families_overlap("แกงจืดต้นคะน้า", "Egg Fried Rice", self.KEYWORD_PAIRS)
        )

    def test_thai_keyword_alone_without_matching_english_form_is_not_overlap(self):
        # "กุ้ง" (shrimp) appears in this Thai name, but no fixture-side
        # keyword is present in "Egg Fried Rice" -- confirms this is NOT a
        # plain single-language substring check (that would be too broad,
        # matching e.g. any shrimp dish against any unrelated fixture).
        self.assertFalse(
            dish_families_overlap("กุ้งทาพริกไทยกระเทียม", "Egg Fried Rice", self.KEYWORD_PAIRS)
        )


if __name__ == "__main__":
    unittest.main()
