from copy import deepcopy
import json
import unittest

from recipe_instructions import (
    generation_schema, instruction_registry, normalize_generated_recipe,
    instruction_uses, public_recipe,
)
from recipe_checks import check_ingredients, check_logic


def wire_recipe():
    return {"recipe_name": "Spinach Salad", "servings": 1,
            "estimated_total_time": {"min_minutes": 5, "max_minutes": 10},
            "adjusted_ingredients": ["ผักปวยเล้ง 100 กรัม", "แตงกวา 50 กรัม"],
            "instructions": [{"action": "mix", "ingredients": ["i1", "i2"], "targets": [], "excluded": []}],
            "diet_tags": ["Thai"], "safety_warning": "ระวังความร้อน",
            "nutrition": {"basis": "per_serving", "calories": 100, "protein_g": 2, "carbs_g": 10, "fat_g": 5}}


SELECTED = ["spinach", "cucumber"]


class StructuredInstructionTests(unittest.TestCase):
    def test_total_time_is_preserved_without_changing_input(self):
        raw = wire_recipe()
        original = deepcopy(raw)
        recipe = normalize_generated_recipe(raw, SELECTED)
        self.assertEqual(public_recipe(recipe)["estimated_total_time"], raw["estimated_total_time"])
        self.assertEqual(raw, original)
        time_schema = generation_schema(SELECTED)["properties"]["estimated_total_time"]["anyOf"]
        self.assertEqual(time_schema[1], {"type": "null"})
        self.assertFalse(time_schema[0]["additionalProperties"])
        self.assertEqual(time_schema[0]["properties"]["min_minutes"]["minimum"], 1)

    def test_missing_or_invalid_total_time_alone_becomes_unknown(self):
        for value in (None, {}, [], "15–20", {"min_minutes": 1},
                      {"min_minutes": 20, "max_minutes": 10},
                      {"min_minutes": 1, "max_minutes": 5, "text": "extra"}):
            with self.subTest(value=value):
                raw = wire_recipe()
                raw["estimated_total_time"] = value
                original = deepcopy(raw)
                self.assertIsNone(normalize_generated_recipe(raw, SELECTED)["estimated_total_time"])
                self.assertEqual(raw, original)
        for value in (True, 0, -1, 1.5, "5", float("nan"), float("inf"), 2**53, 10**400):
            for key in ("min_minutes", "max_minutes"):
                with self.subTest(value=value, key=key):
                    raw = wire_recipe()
                    raw["estimated_total_time"][key] = value
                    self.assertIsNone(normalize_generated_recipe(raw, SELECTED)["estimated_total_time"])
        raw = wire_recipe()
        raw.pop("estimated_total_time")
        self.assertIsNone(normalize_generated_recipe(raw, SELECTED)["estimated_total_time"])
        for key in ("servings", "nutrition", "safety_warning"):
            with self.subTest(missing=key):
                invalid = {**raw, "estimated_total_time": "bad"}
                invalid.pop(key)
                with self.assertRaises(ValueError):
                    normalize_generated_recipe(invalid, SELECTED)

    def test_mix_has_no_kale_false_positive_and_preserves_public_strings(self):
        raw = wire_recipe()
        original = deepcopy(raw)
        recipe = normalize_generated_recipe(raw, SELECTED)
        self.assertEqual(raw, original)
        self.assertIn("คลุกเคล้า", recipe["instructions"][0])
        self.assertEqual(check_logic(recipe), (True, "OK"))
        self.assertEqual(check_ingredients(recipe, SELECTED), (True, "OK"))
        self.assertEqual(instruction_uses(recipe)[0], ["spinach", "cucumber"])
        shown = public_recipe(recipe)
        self.assertNotIn("_instruction_plan", shown)
        self.assertTrue(all(isinstance(step, str) for step in shown["instructions"]))
        json.dumps(shown, ensure_ascii=False)

    def test_excluded_known_food_does_not_require_a_declaration(self):
        raw = wire_recipe()
        raw["instructions"][0]["excluded"] = ["i3"]
        recipe = normalize_generated_recipe(raw, SELECTED + ["shrimp"])
        self.assertIn("ไม่ใส่", recipe["instructions"][0])
        self.assertNotIn("shrimp", instruction_uses(recipe)[0])
        self.assertTrue(check_logic(recipe)[0])

    def test_unknown_undeclared_and_conflicting_ids_are_rejected(self):
        for change in [
            {"ingredients": ["i999"]},
            {"ingredients": ["i3"]},
            {"ingredients": ["i1"], "excluded": ["i1"]},
            {"ingredients": ["i1", "i1"]},
            {"excluded": ["i999"]},
        ]:
            with self.subTest(change=change):
                raw = wire_recipe()
                raw["instructions"][0].update(change)
                with self.assertRaises(ValueError):
                    normalize_generated_recipe(raw, SELECTED + ["shrimp"])

    def test_free_text_foreign_scripts_and_hidden_food_fields_are_rejected(self):
        for steps in [
            ["คลุกผักแล้วใส่ทุเรียน"],
            [{"action": "mix", "ingredients": ["i1"], "excluded": [], "text": "เติมทุเรียน"}],
            [{"action": "เติมทุเรียน", "ingredients": ["i1"], "excluded": []}],
            [{"action": "mix", "ingredients": ["ทุเรียน"], "excluded": []}],
            [{"action": "mix", "ingredients": ["i1"], "excluded": [], "detail": "加入虾"}],
        ]:
            raw = wire_recipe()
            raw["instructions"] = steps
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                normalize_generated_recipe(raw, SELECTED)
        raw = wire_recipe()
        raw["safety_warning"] = "ระวัง 开"
        with self.assertRaises(ValueError):
            normalize_generated_recipe(raw, SELECTED)

    def test_custom_selected_food_and_thai_action_junctions(self):
        for name in ["ทุเรียน", "dragon fruit", "cherry tomatoes", "เต้าหู้ทอด", "fried tofu"]:
            raw = wire_recipe()
            raw["recipe_name"] = "Prepared Food"
            raw["adjusted_ingredients"] = [name + " 100 กรัม"]
            raw["instructions"] = [{"action": "cut", "ingredients": ["i1"], "excluded": []}]
            recipe = normalize_generated_recipe(raw, [name])
            self.assertEqual(check_logic(recipe), (True, "OK"))
            self.assertTrue(check_ingredients(recipe, [name])[0])

    def test_oil_rules_still_require_declared_and_used_oil(self):
        raw = wire_recipe()
        raw["instructions"][0]["action"] = "stir_fry"
        self.assertFalse(check_logic(normalize_generated_recipe(raw, SELECTED))[0])
        refs = instruction_registry(SELECTED)
        oil_id = next(key for key, value in refs.items() if value == "oil")
        raw["adjusted_ingredients"].append("น้ำมัน 1 ช้อนโต๊ะ")
        self.assertFalse(check_logic(normalize_generated_recipe(raw, SELECTED))[0])
        raw["instructions"][0]["ingredients"].append(oil_id)
        self.assertTrue(check_logic(normalize_generated_recipe(raw, SELECTED))[0])
        raw["instructions"][0].update(action="air_fry", ingredients=["i1"])
        self.assertTrue(check_logic(normalize_generated_recipe(raw, SELECTED))[0])

    def test_forged_or_mutated_internal_plan_cannot_bypass_checks(self):
        recipe = normalize_generated_recipe(wire_recipe(), SELECTED)
        recipe["instructions"][0] += " แล้วเติมทุเรียน"
        with self.assertRaises(ValueError):
            instruction_uses(recipe)
        self.assertFalse(check_ingredients(recipe, SELECTED)[0])
        raw = wire_recipe()
        raw["_instruction_plan"] = []
        with self.assertRaises(ValueError):
            normalize_generated_recipe(raw, SELECTED)

    def test_timing_is_numeric_and_unknown_step_fields_fail_closed(self):
        for value in [True, -1, 0, float("nan"), float("inf"), "จนเป็นสีน้ำตาล"]:
            raw = wire_recipe()
            raw["instructions"][0]["minutes"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_generated_recipe(raw, SELECTED)
        raw = wire_recipe()
        raw["instructions"][0].update(minutes=2, temperature_c=180)
        recipe = normalize_generated_recipe(raw, SELECTED)
        self.assertIn("2 นาที", recipe["instructions"][0])
        self.assertIn("180", recipe["instructions"][0])

    def test_shared_schema_defines_actions_ids_and_no_raw_step_text(self):
        schema = generation_schema(SELECTED)
        shapes = schema["properties"]["instructions"]["items"]["anyOf"]
        self.assertTrue(any("mix" in shape["properties"]["action"]["enum"] for shape in shapes))
        for shape in shapes:
            self.assertFalse(shape["additionalProperties"])
            self.assertIn("i1", shape["properties"]["ingredients"]["items"]["enum"])
            self.assertNotIn("text", shape["properties"])

    def test_flavor_tracks_inherited_mixture_and_additions_after_frying(self):
        from recipe_checks import check_flavor
        raw = wire_recipe()
        raw.update(recipe_name="Pad Kra Pao", adjusted_ingredients=["นมวัว 50 กรัม", "น้ำปลา 5 กรัม"])
        selected = ["cow milk", "fish sauce"]
        raw["instructions"] = [{"action": "mix", "ingredients": ["i1", "i2"], "excluded": []},
                               {"action": "stir_fry", "ingredients": [], "excluded": []}]
        self.assertFalse(check_flavor(normalize_generated_recipe(raw, selected))[0])
        raw["instructions"] = [{"action": "stir_fry", "ingredients": ["i1"], "excluded": []},
                               {"action": "add", "ingredients": ["i2"], "excluded": []}]
        self.assertFalse(check_flavor(normalize_generated_recipe(raw, selected))[0])
        raw["instructions"].insert(1, {"action": "serve_separately", "ingredients": [], "excluded": []})
        self.assertTrue(check_flavor(normalize_generated_recipe(raw, selected))[0])
