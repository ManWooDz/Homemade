import unittest

from finetune.recipe_source import Recipe, parse_ingredient_block


class ParseIngredientBlockTests(unittest.TestCase):
    def test_splits_bulleted_lines_into_list(self):
        raw = "- กุ้งนาง 4 ตัว\n\n- พริกไทย 5 เม็ด\n\n- น้ำปลา 2 ช้อนโต๊ะ"
        self.assertEqual(
            parse_ingredient_block(raw),
            ["กุ้งนาง 4 ตัว", "พริกไทย 5 เม็ด", "น้ำปลา 2 ช้อนโต๊ะ"],
        )

    def test_empty_or_non_string_input_returns_empty_list(self):
        self.assertEqual(parse_ingredient_block(""), [])
        self.assertEqual(parse_ingredient_block(None), [])


class RecipeDataclassTests(unittest.TestCase):
    def test_recipe_holds_expected_fields(self):
        r = Recipe(dish_name="ต้มยำกุ้ง", ingredient_lines=["กุ้ง 3 ตัว"], instruction_text="ต้มน้ำ")
        self.assertEqual(r.dish_name, "ต้มยำกุ้ง")
        self.assertEqual(r.ingredient_lines, ["กุ้ง 3 ตัว"])
        self.assertEqual(r.instruction_text, "ต้มน้ำ")


if __name__ == "__main__":
    unittest.main()
