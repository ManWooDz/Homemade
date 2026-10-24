import ast
from pathlib import Path
import unittest

from recipe_instructions import (FORMAT_ERROR, generation_schema, normalize_generated_recipe,
                                 public_recipe)
from recipe_checks import check_ingredients, check_flavor, check_logic, check_nutrition, check_core
from recipe_contracts import validate_generated_recipe_shape
from allergen_kg.match import find_allergy_violation, format_violation_reason
from test_instruction_workflow import step
from test_instruction_schema import role_shape_accepts
from test_recipe_instructions import wire_recipe


class CookingMediumTests(unittest.TestCase):
    def recipe(self, selected, steps, name="Prepared Food"):
        raw = wire_recipe()
        raw.update(recipe_name=name, adjusted_ingredients=[name + " 100 กรัม" for name in selected], instructions=steps)
        return normalize_generated_recipe(raw, selected, require_workflow=True)

    def test_frying_renders_known_oils_as_medium_without_losing_positive_references(self):
        for oil in ("oil", "vegetable oil", "olive oil"):
            for action, verb in (("fry", "ทอด"), ("stir_fry", "ผัด")):
                with self.subTest(oil=oil, action=action):
                    recipe = self.recipe([oil, "ไข่ไก่"], [step(action, ["i1", "i2"])])
                    self.assertTrue(recipe["instructions"][0].startswith(verb + "ไข่ไก่"))
                    self.assertIn("น้ำมัน", recipe["instructions"][0])
                    self.assertEqual(recipe["_instruction_plan"][0]["ingredients"], [oil, "ไข่ไก่"])
                    self.assertTrue(check_ingredients(recipe, [oil, "ไข่ไก่"])[0])
                    self.assertTrue(check_logic(recipe)[0])

    def test_oil_only_frying_is_refused_at_logic_and_oil_heating_is_valid(self):
        for action in ("fry", "stir_fry"):
            recipe = self.recipe(["vegetable oil"], [step(action, ["i1"])])
            valid, reason = check_logic(recipe)
            self.assertFalse(valid)
            self.assertIn("Oil-only frying", reason)
        self.assertTrue(check_logic(self.recipe(["vegetable oil"], [step("heat", ["i1"])]))[0])

    def test_new_oil_heat_cycle_requires_an_explicit_transfer(self):
        selected = ["vegetable oil", "ไข่ไก่", "minced pork"]
        steps = [step("fry", ["i1", "i2"]), step("heat", ["i1"]), step("stir_fry", ["i3"])]
        valid, reason = check_logic(self.recipe(selected, steps))
        self.assertFalse(valid)
        self.assertIn("set_aside", reason)
        steps.insert(1, step("set_aside", targets=["i2"]))
        steps.append(step("serve", ["i2"], ["i3"]))
        recipe = self.recipe(selected, steps)
        self.assertTrue(check_logic(recipe)[0])
        self.assertEqual(recipe["instructions"][1], "ตักไข่ไก่ขึ้นพักไว้")
        self.assertTrue(all(isinstance(line, str) for line in public_recipe(recipe)["instructions"]))

    def test_direct_sequential_cooking_or_explicit_food_reheating_does_not_require_transfer(self):
        selected = ["vegetable oil", "ไข่ไก่", "minced pork"]
        start = [step("fry", ["i1", "i2"])]
        self.assertTrue(check_logic(self.recipe(selected, start + [step("stir_fry", ["i3"])]))[0])
        self.assertTrue(check_logic(self.recipe(selected, start + [step("heat", ["i1", "i2"]), step("stir_fry", ["i3"])]))[0])

    def test_partial_transfer_does_not_clear_unrelated_pan_food(self):
        selected = ["oil", "egg", "shrimp"]
        steps = [step("fry", ["i1", "i2", "i3"]), step("set_aside", targets=["i2"]), step("heat", ["i1"])]
        self.assertFalse(check_logic(self.recipe(selected, steps))[0])
        steps.insert(2, step("serve_separately", targets=["i3"]))
        self.assertTrue(check_logic(self.recipe(selected, steps))[0])

    def test_served_components_clear_only_the_explicitly_served_food(self):
        selected = ["oil", "egg", "minced pork"]
        steps = [step("fry", ["i1", "i2"]), step("serve_separately", targets=["i2"]),
                 step("heat", ["i1"]), step("stir_fry", ["i3"])]
        self.assertTrue(check_logic(self.recipe(selected, steps))[0])

    def test_set_aside_requires_one_known_declared_positive_role_and_is_not_cooking(self):
        schema = generation_schema(["egg"])["properties"]["instructions"]["items"]
        for value in (step("set_aside", ["i1"]), step("set_aside", targets=["i1"])):
            self.assertTrue(role_shape_accepts(schema, value))
            recipe = self.recipe(["egg"], [value, step("serve", targets=["i1"])])
            self.assertFalse(check_logic(recipe)[0])
        for value in (step("set_aside"), step("set_aside", ["i1"], ["i2"]),
                      step("set_aside", targets=["i999"]), step("set_aside", targets=["i1", "i1"])):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.recipe(["egg", "water"], [value])

    def test_set_aside_removes_explicit_flavor_component_without_clearing_unrelated_food(self):
        selected = ["cow milk", "fish sauce", "oil", "garlic"]
        start = [step("heat", ["i3"]), step("stir_fry", ["i1", "i4"])]
        separate = start + [step("set_aside", ["i1"]), step("stir_fry", ["i2"])]
        self.assertTrue(check_flavor(self.recipe(selected, separate, "Pad Kra Pao"))[0])
        together = start + [step("set_aside", ["i4"]), step("add", ["i2"], ["i1"])]
        self.assertFalse(check_flavor(self.recipe(selected, together, "Pad Kra Pao"))[0])

    def test_allergy_still_precedes_pan_quality_refusal(self):
        source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
        functions = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
                     and node.name in ("check_allergy", "validate_recipe")]
        namespace = dict(globals())
        exec(compile(ast.Module(body=functions, type_ignores=[]), "main.py", "exec"), namespace)
        recipe = self.recipe(["oil", "shrimp"], [step("fry", ["i1", "i2"]), step("heat", ["i1"])])
        self.assertFalse(check_logic(recipe)[0])
        result = namespace["validate_recipe"](recipe, ["oil", "shrimp"], {"allergies": "shrimp"}, resolved_blocks={})
        self.assertEqual(result["status"], "fail")
        self.assertIn("shrimp", result["reason"])
        self.assertNotIn("set_aside", result["reason"])
