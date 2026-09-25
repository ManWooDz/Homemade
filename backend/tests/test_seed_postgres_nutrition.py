import unittest

from database.seed_postgres import MOCK_RECIPES


class MockRecipesHaveQuantitiesTests(unittest.TestCase):
    def test_every_recipe_has_servings_and_matching_quantity_names(self):
        for recipe in MOCK_RECIPES:
            self.assertIsInstance(recipe.get("servings"), int)
            quantity_names = [q["name"] for q in recipe.get("ingredient_quantities", [])]
            self.assertEqual(quantity_names, recipe["ingredients"], f"{recipe['name']}: must be parallel to ingredients")


if __name__ == "__main__":
    unittest.main()
