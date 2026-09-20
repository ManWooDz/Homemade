import unittest
from unittest.mock import patch, MagicMock

import pandas as pd

from finetune.recipe_source import (
    Recipe,
    parse_ingredient_block,
    _extract_ingredient_section_from_text,
    _extract_instruction_section_from_text,
    load_recipes,
)


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

    def test_drops_bare_dash_lines_with_no_content(self):
        """Lines that are just '-' or '-  ' (dash plus whitespace) should not
        produce empty strings in the result."""
        raw = "- กุ้งนาง 4 ตัว\n\n- \n\n- พริกไทย 5 เม็ด\n\n-   \n\n- น้ำปลา 2 ช้อนโต๊ะ"
        self.assertEqual(
            parse_ingredient_block(raw),
            ["กุ้งนาง 4 ตัว", "พริกไทย 5 เม็ด", "น้ำปลา 2 ช้อนโต๊ะ"],
        )
        # Verify no empty strings in result
        result = parse_ingredient_block(raw)
        self.assertNotIn("", result)


class RecipeDataclassTests(unittest.TestCase):
    def test_recipe_holds_expected_fields(self):
        r = Recipe(dish_name="ต้มยำกุ้ง", ingredient_lines=["กุ้ง 3 ตัว"], instruction_text="ต้มน้ำ")
        self.assertEqual(r.dish_name, "ต้มยำกุ้ง")
        self.assertEqual(r.ingredient_lines, ["กุ้ง 3 ตัว"])
        self.assertEqual(r.instruction_text, "ต้มน้ำ")


class ExtractIngredientSectionTests(unittest.TestCase):
    def test_extracts_ingredient_section_from_markdown(self):
        """Test extraction of ingredient section bounded by markdown headers."""
        text = "## เครื่องปรุง\n- กุ้งนาง 4 ตัว\n- พริกไทย 5 เม็ด\n## วิธีทำ\nต้มน้ำ"
        result = _extract_ingredient_section_from_text(text)
        self.assertIn("กุ้งนาง 4 ตัว", result)
        self.assertIn("พริกไทย 5 เม็ด", result)
        self.assertNotIn("วิธีทำ", result)

    def test_extracts_ingredient_without_instruction_header(self):
        """If instruction header is missing, still extract everything after ingredient header."""
        text = "## เครื่องปรุง\n- กุ้งนาง 4 ตัว\n- พริกไทย 5 เม็ด\nจบแล้ว"
        result = _extract_ingredient_section_from_text(text)
        self.assertIn("กุ้งนาง 4 ตัว", result)
        self.assertIn("พริกไทย 5 เม็ด", result)
        # should include everything after header if no next section
        self.assertIn("จบแล้ว", result)

    def test_returns_empty_if_ingredient_header_missing(self):
        text = "## วิธีทำ\nต้มน้ำ"
        result = _extract_ingredient_section_from_text(text)
        self.assertEqual(result, "")

    def test_returns_empty_if_input_not_string(self):
        self.assertEqual(_extract_ingredient_section_from_text(None), "")
        self.assertEqual(_extract_ingredient_section_from_text(123), "")


class ExtractInstructionSectionTests(unittest.TestCase):
    def test_extracts_instruction_section_from_markdown(self):
        text = "## เครื่องปรุง\n- กุ้งนาง\n## วิธีทำ\nล้างกุ้ง\nตั้งไฟ"
        result = _extract_instruction_section_from_text(text)
        self.assertIn("ล้างกุ้ง", result)
        self.assertIn("ตั้งไฟ", result)
        self.assertNotIn("เครื่องปรุง", result)

    def test_returns_empty_if_instruction_header_missing(self):
        text = "## เครื่องปรุง\n- กุ้งนาง"
        result = _extract_instruction_section_from_text(text)
        self.assertEqual(result, "")

    def test_returns_empty_if_input_not_string(self):
        self.assertEqual(_extract_instruction_section_from_text(None), "")
        self.assertEqual(_extract_instruction_section_from_text(123), "")


class LoadRecipesWithFallbackTests(unittest.TestCase):
    def test_falls_back_to_text_column_when_ingredient_missing(self):
        """When Ingredient column is empty/missing but text column has markdown,
        load_recipes should extract ingredients from text."""
        # Create a mock DataFrame with one row: empty Ingredient, but text has markdown
        data = {
            "DishName": ["ต้มยำกุ้ง"],
            "Ingredient": [""],  # empty ingredient column
            "Instruction": ["ต้มน้ำ"],
            "text": [
                "# ต้มยำกุ้ง\n## เครื่องปรุง\n- กุ้งนาง 4 ตัว\n- พริกไทย 5 เม็ด\n## วิธีทำ\nต้มน้ำ"
            ],
        }
        df = pd.DataFrame(data)

        with patch("finetune.recipe_source.pd.read_excel", return_value=df):
            recipes = load_recipes("dummy_path.xlsx")
            self.assertEqual(len(recipes), 1)
            self.assertEqual(recipes[0].dish_name, "ต้มยำกุ้ง")
            self.assertIn("กุ้งนาง 4 ตัว", recipes[0].ingredient_lines)
            self.assertIn("พริกไทย 5 เม็ด", recipes[0].ingredient_lines)

    def test_falls_back_to_text_column_when_instruction_missing(self):
        """When Instruction column is empty/missing but text column has markdown,
        load_recipes should extract instructions from text."""
        data = {
            "DishName": ["ต้มยำกุ้ง"],
            "Ingredient": ["- กุ้งนาง 4 ตัว\n- พริกไทย 5 เม็ด"],
            "Instruction": [""],  # empty instruction column
            "text": [
                "# ต้มยำกุ้ง\n## เครื่องปรุง\n- กุ้งนาง 4 ตัว\n## วิธีทำ\nล้างกุ้ง\nตั้งไฟ"
            ],
        }
        df = pd.DataFrame(data)

        with patch("finetune.recipe_source.pd.read_excel", return_value=df):
            recipes = load_recipes("dummy_path.xlsx")
            self.assertEqual(len(recipes), 1)
            self.assertEqual(recipes[0].dish_name, "ต้มยำกุ้ง")
            self.assertIn("ล้างกุ้ง", recipes[0].instruction_text)
            self.assertIn("ตั้งไฟ", recipes[0].instruction_text)

    def test_skips_row_if_neither_ingredient_nor_text_fallback_available(self):
        """If Ingredient column is empty and text doesn't have ingredient header,
        skip the row."""
        data = {
            "DishName": ["ต้มยำกุ้ง"],
            "Ingredient": [""],
            "Instruction": ["ต้มน้ำ"],
            "text": ["# ต้มยำกุ้ง\nจะทำอย่างไร"],  # no markdown headers
        }
        df = pd.DataFrame(data)

        with patch("finetune.recipe_source.pd.read_excel", return_value=df):
            recipes = load_recipes("dummy_path.xlsx")
            self.assertEqual(len(recipes), 0)  # row should be skipped

    def test_skips_row_if_neither_instruction_nor_text_fallback_available(self):
        """If Instruction column is empty and text doesn't have instruction header,
        skip the row."""
        data = {
            "DishName": ["ต้มยำกุ้ง"],
            "Ingredient": ["- กุ้งนาง 4 ตัว"],
            "Instruction": [""],
            "text": ["# ต้มยำกุ้ง\nมีแต่เครื่องปรุง\n## เครื่องปรุง\n- กุ้ง"],  # no instruction header
        }
        df = pd.DataFrame(data)

        with patch("finetune.recipe_source.pd.read_excel", return_value=df):
            recipes = load_recipes("dummy_path.xlsx")
            self.assertEqual(len(recipes), 0)  # row should be skipped (no instructions)


if __name__ == "__main__":
    unittest.main()
