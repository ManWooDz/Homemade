import re
import unittest

from recipe_instructions import generation_schema, instruction_prompt, normalize_generated_recipe
from test_recipe_instructions import SELECTED, wire_recipe


class DeclarationFormatTests(unittest.TestCase):
    def test_schema_forbids_quantity_first_and_id_annotations(self):
        pattern = generation_schema(["minced pork"])['properties']['adjusted_ingredients']['items']['pattern']
        for line in ("300 กรัม หมูสับ (i1)", "300 กรัม หมูสับ", "หมูสับ 300 กรัม (i1)", "หมูสับ (i1) 300 กรัม"):
            with self.subTest(line=line):
                self.assertIsNone(re.fullmatch(pattern, line))
        self.assertIsNotNone(re.fullmatch(pattern, "หมูสับ 300 กรัม"))

    def test_runtime_rejects_format_with_actionable_feedback(self):
        for line in ("100 กรัม ผักปวยเล้ง (i1)", "100 กรัม ผักปวยเล้ง", "ผักปวยเล้ง 100 กรัม (i1)"):
            raw = wire_recipe()
            raw['adjusted_ingredients'][0] = line
            with self.subTest(line=line), self.assertRaisesRegex(ValueError, "declaration format.*name.*quantity"):
                normalize_generated_recipe(raw, SELECTED)

    def test_supported_declarations_keep_quantities_and_custom_names(self):
        for name in ("spinach", "ผักปวยเล้ง", "dragon fruit", "สมุนไพร 12 ชนิด", "pork belly (chashu)"):
            for amount in ("100 กรัม", "5-7 เม็ด", "1/2 ถ้วย", "ตามชอบ", "(ตามชอบ)", ""):
                with self.subTest(name=name, amount=amount):
                    raw = wire_recipe()
                    raw.update(recipe_name="Prepared Food", adjusted_ingredients=[(name + " " + amount).strip()],
                               instructions=[{"action":"cut", "ingredients":["i1"], "excluded":[]}])
                    recipe = normalize_generated_recipe(raw, [name])
                    self.assertEqual(recipe['adjusted_ingredients'], raw['adjusted_ingredients'])

    def test_prompt_states_exact_order_and_id_scope(self):
        prompt = instruction_prompt(SELECTED)
        self.assertIn("หมูสับ 300 กรัม", prompt)
        self.assertIn("ห้ามใส่รหัส iN", prompt)
