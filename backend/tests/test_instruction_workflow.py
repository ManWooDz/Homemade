import json
import unittest

from recipe_instructions import (FORMAT_ERROR, generation_schema, normalize_generated_recipe,
                                 parse_generated_recipe, public_recipe)
from test_recipe_instructions import wire_recipe
from recipe_checks import check_logic


def step(action, ingredients=(), targets=()):
    return {"action": action, "ingredients": list(ingredients), "targets": list(targets), "excluded": []}


class WorkflowTests(unittest.TestCase):
    def recipe(self, selected, steps):
        raw = wire_recipe()
        raw.update(recipe_name="Prepared Food", adjusted_ingredients=[name + " 100 กรัม" for name in selected], instructions=steps)
        recipe = normalize_generated_recipe(raw, selected)
        valid, reason = check_logic(recipe)
        if not valid:
            raise ValueError(reason)
        return recipe

    def test_first_season_has_explicit_food_target(self):
        recipe = self.recipe(["beef steak", "salt"], [step("season", ["i2"], ["i1"]), step("grill", ["i1"])])
        self.assertIn("ปรุงรสเนื้อวัวสำหรับสเต๊กด้วยเกลือ", recipe['instructions'][0])
        self.assertNotIn("ขั้นตอนก่อนหน้า", recipe['instructions'][0])
        with self.assertRaisesRegex(ValueError, "targets"):
            self.recipe(["salt"], [step("season", ["i1"])])

    def test_serve_meal_with_garnish_instead_of_garnish_alone(self):
        recipe = self.recipe(["shrimp", "cilantro"], [step("boil", ["i1"]), step("serve", ["i2"], ["i1"])])
        self.assertIn("กุ้ง", recipe['instructions'][-1])
        self.assertIn("ผักชี", recipe['instructions'][-1])
        self.assertNotEqual(recipe['instructions'][-1], "จัดเสิร์ฟผักชี")
        with self.assertRaisesRegex(ValueError, "targets"):
            self.recipe(["cilantro"], [step("serve", ["i1"])])

    def test_beating_or_adding_does_not_count_as_cooking(self):
        for food, action in [("egg", "beat"), ("minced pork", "add"), ("shrimp", "add")]:
            with self.subTest(food=food), self.assertRaisesRegex(ValueError, "cooking"):
                self.recipe([food, "water"], [step("mix", ["i2"]), step(action, ["i1"], ["i2"] if action == "add" else []), step("serve", targets=["i1"])])
        recipe = self.recipe(["egg", "water"], [step("beat", ["i1"]), step("boil", ["i1", "i2"]), step("serve", targets=["i1"])])
        self.assertTrue(recipe['instructions'])

    def test_cooking_after_serve_does_not_retroactively_pass(self):
        with self.assertRaisesRegex(ValueError, "cooking"):
            self.recipe(["egg"], [step("beat", ["i1"]), step("serve", targets=["i1"]), step("boil", ["i1"])])

    def test_target_roles_are_known_declared_and_nonconflicting(self):
        for targets in (["i999"], ["i2"], ["i1", "i1"], ["i1"]):
            raw = wire_recipe()
            raw['adjusted_ingredients'] = ["spinach 100 กรัม"]
            raw['instructions'] = [step("mix", ["i1"], targets)]
            with self.subTest(targets=targets), self.assertRaises(ValueError):
                normalize_generated_recipe(raw, ["spinach", "cucumber"])

    def test_ready_food_and_vegetables_do_not_require_a_cooking_action(self):
        for name in ("soft-boiled egg", "pork belly (chashu)", "cucumber", "dragon fruit"):
            with self.subTest(name=name):
                self.recipe([name], [step("cut", ["i1"]), step("serve", targets=["i1"])])

    def test_separate_ready_component_can_be_served_before_other_protein_is_cooked(self):
        self.recipe(["egg", "spinach"], [step("beat", ["i1"]), step("serve_separately", targets=["i2"]),
                                         step("boil", ["i1"]), step("serve", targets=["i1"])])

    def test_rest_and_drain_do_not_hide_an_ingredient_role(self):
        for action in ("rest", "drain"):
            with self.subTest(action=action):
                recipe = self.recipe(["spinach"], [step(action, targets=["i1"])])
                self.assertIn("ผักปวยเล้ง", recipe['instructions'][0])
                with self.assertRaisesRegex(ValueError, "not both"):
                    self.recipe(["spinach", "cucumber"], [step(action, ["i2"], ["i1"])])

    def test_current_provider_boundary_requires_targets_and_keeps_public_strings(self):
        raw = wire_recipe()
        raw['instructions'] = [{"action": "mix", "ingredients": ["i1"], "excluded": []}]
        self.assertIn(FORMAT_ERROR, parse_generated_recipe(json.dumps(raw), ["spinach", "cucumber"]))
        raw['instructions'] = [step("mix", ["i1", "i2"])]
        result = parse_generated_recipe(json.dumps(raw), ["spinach", "cucumber"])
        self.assertNotIn(FORMAT_ERROR, result)
        self.assertTrue(all(isinstance(item, str) for item in public_recipe(result)['instructions']))
        self.assertFalse(any(key.startswith('_') for key in public_recipe(result)))
        for shape in generation_schema(["spinach"])['properties']['instructions']['items']['anyOf']:
            self.assertIn("targets", shape['required'])
        raw['_instruction_protocol'] = 1
        self.assertIn(FORMAT_ERROR, parse_generated_recipe(json.dumps(raw), ["spinach", "cucumber"]))
