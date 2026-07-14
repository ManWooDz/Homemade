import unittest
from copy import deepcopy
from types import SimpleNamespace

from recipe_contracts import ingredient_names, validate_generated_recipe_shape


VALID_RECIPE = {
    "recipe_name": "Thai Basil Pork",
    "servings": 2,
    "adjusted_ingredients": ["minced pork 200 grams"],
    "diet_tags": ["Thai"],
    "nutrition": {
        "basis": "per_serving",
        "calories": 420,
        "protein_g": 28,
        "carbs_g": 18,
        "fat_g": 24,
    },
    "instructions": ["Cook the minced pork thoroughly."],
    "safety_warning": "Use care around the hot pan.",
}


class RecipeContractTests(unittest.TestCase):
    def test_ingredient_names_ignore_fridge_quantity_and_metadata(self):
        result = ingredient_names(
            [
                {"id": 1, "name": " minced pork ", "quantity": "250 grams"},
                SimpleNamespace(name=" basil ", quantity="1 bunch"),
            ]
        )
        self.assertEqual(result, ["minced pork", "basil"])

    def test_ingredient_names_support_legacy_strings(self):
        self.assertEqual(ingredient_names([" egg "]), ["egg"])

    def test_blank_or_missing_ingredient_name_is_rejected(self):
        invalid_items = [{"name": " "}, {}, SimpleNamespace(quantity="1 cup")]
        for item in invalid_items:
            with self.subTest(item=item):
                with self.assertRaisesRegex(ValueError, "Ingredient name is required"):
                    ingredient_names([item])

    def test_valid_recipe_shape_passes(self):
        valid, reason = validate_generated_recipe_shape(deepcopy(VALID_RECIPE))
        self.assertEqual((valid, reason), (True, "OK"))

    def test_non_dictionary_recipe_is_safely_rejected(self):
        for recipe in (None, [], "recipe"):
            with self.subTest(recipe=recipe):
                try:
                    result = validate_generated_recipe_shape(recipe)
                except Exception as exc:
                    self.fail(f"validation raised {type(exc).__name__}: {exc}")
                self.assertEqual(result, (False, "Invalid recipe"))

    def test_missing_or_blank_recipe_name_fails(self):
        for recipe_name in (None, "", "   ", 42):
            with self.subTest(recipe_name=recipe_name):
                recipe = deepcopy(VALID_RECIPE)
                if recipe_name is None:
                    recipe.pop("recipe_name")
                else:
                    recipe["recipe_name"] = recipe_name

                valid, reason = validate_generated_recipe_shape(recipe)
                self.assertEqual((valid, reason), (False, "Invalid recipe name"))

    def test_invalid_servings_fail(self):
        for servings in (None, True, 0, 1.5):
            with self.subTest(servings=servings):
                recipe = deepcopy(VALID_RECIPE)
                if servings is None:
                    recipe.pop("servings")
                else:
                    recipe["servings"] = servings

                valid, reason = validate_generated_recipe_shape(recipe)
                self.assertEqual((valid, reason), (False, "Invalid servings"))

    def test_invalid_or_empty_adjusted_ingredients_fail(self):
        for ingredients in (None, [], [" "], [1]):
            with self.subTest(ingredients=ingredients):
                recipe = deepcopy(VALID_RECIPE)
                if ingredients is None:
                    recipe.pop("adjusted_ingredients")
                else:
                    recipe["adjusted_ingredients"] = ingredients

                valid, reason = validate_generated_recipe_shape(recipe)
                self.assertEqual(
                    (valid, reason), (False, "Invalid adjusted ingredients")
                )

    def test_invalid_or_empty_instructions_fail(self):
        for instructions in (None, [], [" "], [1]):
            with self.subTest(instructions=instructions):
                recipe = deepcopy(VALID_RECIPE)
                if instructions is None:
                    recipe.pop("instructions")
                else:
                    recipe["instructions"] = instructions

                valid, reason = validate_generated_recipe_shape(recipe)
                self.assertEqual((valid, reason), (False, "Invalid instructions"))

    def test_empty_diet_tags_are_allowed(self):
        recipe = deepcopy(VALID_RECIPE)
        recipe["diet_tags"] = []

        valid, reason = validate_generated_recipe_shape(recipe)

        self.assertEqual((valid, reason), (True, "OK"))

    def test_missing_or_invalid_diet_tags_fail(self):
        for diet_tags in (None, "Thai", [" "], [1]):
            with self.subTest(diet_tags=diet_tags):
                recipe = deepcopy(VALID_RECIPE)
                if diet_tags is None:
                    recipe.pop("diet_tags")
                else:
                    recipe["diet_tags"] = diet_tags

                valid, reason = validate_generated_recipe_shape(recipe)
                self.assertEqual((valid, reason), (False, "Invalid diet tags"))

    def test_missing_or_invalid_safety_warning_fails(self):
        for safety_warning in (None, "", " ", []):
            with self.subTest(safety_warning=safety_warning):
                recipe = deepcopy(VALID_RECIPE)
                if safety_warning is None:
                    recipe.pop("safety_warning")
                else:
                    recipe["safety_warning"] = safety_warning

                valid, reason = validate_generated_recipe_shape(recipe)
                self.assertEqual((valid, reason), (False, "Invalid safety warning"))

    def test_wrong_nutrition_basis_fails(self):
        for nutrition in (None, {}, {"basis": "whole_recipe"}):
            with self.subTest(nutrition=nutrition):
                recipe = deepcopy(VALID_RECIPE)
                if nutrition is None:
                    recipe.pop("nutrition")
                else:
                    recipe["nutrition"] = nutrition

                valid, reason = validate_generated_recipe_shape(recipe)
                self.assertEqual((valid, reason), (False, "Invalid nutrition basis"))

    def test_missing_required_nutrients_fail(self):
        for nutrient in ("calories", "protein_g", "carbs_g", "fat_g"):
            with self.subTest(nutrient=nutrient):
                recipe = deepcopy(VALID_RECIPE)
                recipe["nutrition"].pop(nutrient)

                valid, reason = validate_generated_recipe_shape(recipe)
                self.assertEqual(
                    (valid, reason), (False, f"Invalid nutrition value: {nutrient}")
                )

    def test_non_finite_or_non_numeric_nutrients_fail(self):
        invalid_values = (True, "12", -1, float("inf"))
        for nutrient in ("calories", "protein_g", "carbs_g", "fat_g"):
            for value in invalid_values:
                with self.subTest(nutrient=nutrient, value=value):
                    recipe = deepcopy(VALID_RECIPE)
                    recipe["nutrition"][nutrient] = value

                    valid, reason = validate_generated_recipe_shape(recipe)
                    self.assertEqual(
                        (valid, reason),
                        (False, f"Invalid nutrition value: {nutrient}"),
                    )


if __name__ == "__main__":
    unittest.main()
