"""Approved discovery metadata; inspect literals without importing the seeder."""
import ast
from pathlib import Path
import unittest


APPROVED = {
    "Superfood Veggie": (["Healthy / Diet", "Quick & Easy"], ["Brunch", "Lunch", "Dinner", "Picnic"]),
    "Fresh Power Salad": (["Healthy / Diet", "Quick & Easy"], ["Brunch", "Lunch", "Dinner", "Picnic"]),
    "Rainbow Healthy": (["Healthy / Diet", "Quick & Easy"], ["Lunch", "Dinner", "Picnic"]),
    "Chashu Ramen": (["Asian Food", "Japanese Food"], ["Lunch", "Dinner"]),
    "Padthai with shrimps": (["Asian Food", "Thai Food"], ["Lunch", "Dinner"]),
    "Stir-Fried Basil with pork": (["Asian Food", "Thai Food"], ["Lunch", "Dinner", "Spicy"]),
    "Greek Salad": (["Healthy / Diet", "Western Food", "Quick & Easy"], ["Brunch", "Lunch", "Dinner", "Picnic"]),
    "Grilled Steak": (["Western Food", "High Protein"], ["Lunch", "Dinner", "Date Night"]),
    "Tom Yum Kung": (["Asian Food", "Thai Food", "Spicy"], ["Lunch", "Dinner"]),
}


class BaseRecipeTagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path(__file__).resolve().parents[1] / "database/seed_postgres.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        cls.recipes = ast.literal_eval(next(node.value for node in tree.body
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                and target.id == "MOCK_RECIPES" for target in node.targets)))

    def test_exact_approved_additions_preserve_existing_tags_and_order(self):
        self.assertEqual([row["name"] for row in self.recipes], list(APPROVED))
        for row in self.recipes:
            with self.subTest(recipe=row["name"]):
                original, additions = APPROVED[row["name"]]
                self.assertEqual(row["tags"], original + additions)
                self.assertEqual(len(row["tags"]), len(set(row["tags"])))

    def test_no_unapproved_dietary_or_national_cuisine_claims(self):
        forbidden = {"Vegan", "Vegetarian", "Glutan Free", "Gluten Free", "Low Carb", "British", "American", "Kid-Friendly", "Breakfast"}
        for row in self.recipes:
            self.assertFalse(forbidden.intersection(row["tags"]), row["name"])
