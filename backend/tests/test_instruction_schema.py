import json
import unittest

from recipe_instructions import (generation_schema, instruction_prompt, instruction_registry,
                                 _validate_step, _validate_workflow)


def role_shape_accepts(schema, step):
    """Evaluate only the action/role subset of the generated boundary schema."""
    for shape in schema.get("anyOf", [schema]):
        props = shape["properties"]
        if (not set(shape["required"]) <= step.keys()
                or shape.get("additionalProperties") is False and step.keys() - props.keys()
                or step["action"] not in props["action"]["enum"]):
            continue
        for role in ("ingredients", "targets", "excluded"):
            refs, bounds = step[role], props[role]
            if (not isinstance(refs, list) or len(refs) < bounds.get("minItems", 0)
                    or len(refs) > bounds.get("maxItems", float("inf"))
                    or any(ref not in bounds["items"]["enum"] for ref in refs)):
                break
        else:
            return True
    return False


def step(action, ingredients=(), targets=()):
    return {"action": action, "ingredients": list(ingredients), "targets": list(targets), "excluded": []}


class ActionRoleSchemaTests(unittest.TestCase):
    def setUp(self):
        self.schema = generation_schema(["shrimp", "water"])["properties"]["instructions"]["items"]

    def test_cooking_schema_blocks_targets_including_observed_duplicate_roles(self):
        for action in ("fry", "stir_fry", "simmer"):
            with self.subTest(action=action):
                self.assertFalse(role_shape_accepts(self.schema, step(action, ["i1"], ["i1"])))
                self.assertFalse(role_shape_accepts(self.schema, step(action, targets=["i1"])))
                self.assertFalse(role_shape_accepts(self.schema, step(action)))

    def test_add_and_season_require_both_roles(self):
        for action in ("add", "season"):
            with self.subTest(action=action):
                self.assertFalse(role_shape_accepts(self.schema, step(action, ["i1"])))
                self.assertFalse(role_shape_accepts(self.schema, step(action, targets=["i2"])))
                self.assertTrue(role_shape_accepts(self.schema, step(action, ["i1"], ["i2"])))

    def test_serving_requires_main_target_with_optional_garnish(self):
        for action in ("serve", "serve_separately"):
            with self.subTest(action=action):
                self.assertFalse(role_shape_accepts(self.schema, step(action, ["i1"])))
                self.assertTrue(role_shape_accepts(self.schema, step(action, targets=["i1"])))
                self.assertTrue(role_shape_accepts(self.schema, step(action, ["i2"], ["i1"])))

    def test_rest_and_drain_allow_exactly_one_positive_role(self):
        for action in ("rest", "drain"):
            with self.subTest(action=action):
                self.assertFalse(role_shape_accepts(self.schema, step(action)))
                self.assertFalse(role_shape_accepts(self.schema, step(action, ["i1"], ["i2"])))
                self.assertTrue(role_shape_accepts(self.schema, step(action, ["i1"])))
                self.assertTrue(role_shape_accepts(self.schema, step(action, targets=["i1"])))

    def test_ordinary_methods_keep_known_ids_and_no_step_text(self):
        for action in ("wash", "cut", "chop", "slice", "peel", "crush", "beat", "mix", "heat",
                       "stir_fry", "fry", "boil", "simmer", "steam", "bake", "grill", "air_fry",
                       "dry_fry", "water_saute", "marinate"):
            with self.subTest(action=action):
                self.assertTrue(role_shape_accepts(self.schema, step(action, ["i1"])))
                self.assertFalse(role_shape_accepts(self.schema, step(action, ["i999"])))
                self.assertFalse(role_shape_accepts(self.schema, {**step(action, ["i1"]), "text": "เติมทุเรียน"}))

    def test_cross_role_disjointness_still_requires_runtime_validation(self):
        value = step("season", ["i1"], ["i1"])
        self.assertTrue(role_shape_accepts(self.schema, value))
        with self.assertRaises(ValueError):
            _validate_step(value, instruction_registry(["shrimp", "water"]), 1)

    def test_shared_role_examples_use_current_ids_and_pass_real_role_validation(self):
        for selected in (["shrimp", "water"], ["ไข่ไก่"], []):
            with self.subTest(selected=selected):
                prompt = instruction_prompt(selected)
                line = next((line for line in prompt.splitlines() if line.startswith("ตัวอย่างบทบาท JSON: ")), None)
                self.assertIsNotNone(line)
                examples = json.loads(line.removeprefix("ตัวอย่างบทบาท JSON: "))
                self.assertEqual({example["action"] for example in examples},
                                 {"fry", "simmer", "add", "season", "serve", "rest", "drain", "set_aside"})
                schema = generation_schema(selected)["properties"]["instructions"]["items"]
                for example in examples:
                    self.assertTrue(role_shape_accepts(schema, example))
                    _validate_step(example, instruction_registry(selected), 1)
                    _validate_workflow([example])
