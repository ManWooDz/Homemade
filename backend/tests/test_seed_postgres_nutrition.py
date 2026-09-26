import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import (
    Base,
    BaseRecipe,
    IngredientNutrition,
    IngredientNutritionAlias,
    RecipeIngredientImage,
    User,
)
from database.seed_postgres import DEV_USER_EMAIL, MOCK_RECIPES, seed


class MockRecipesHaveQuantitiesTests(unittest.TestCase):
    def test_every_recipe_has_servings_and_matching_quantity_names(self):
        for recipe in MOCK_RECIPES:
            self.assertIsInstance(recipe.get("servings"), int)
            quantity_names = [q["name"] for q in recipe.get("ingredient_quantities", [])]
            self.assertEqual(quantity_names, recipe["ingredients"], f"{recipe['name']}: must be parallel to ingredients")


class SeedResilienceTests(unittest.TestCase):
    """seed() against in-memory SQLite (no live Postgres available)."""

    def setUp(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(
            engine,
            tables=[t.__table__ for t in (User, BaseRecipe, RecipeIngredientImage, IngredientNutrition, IngredientNutritionAlias)],
        )
        self.Session = sessionmaker(bind=engine)
        patcher = patch("database.seed_postgres.SessionLocal", self.Session)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _computed(self, name):
        return {"basis": "per_serving", "calories": float(len(name)), "protein_g": 1.0, "carbs_g": 1.0, "fat_g": 1.0}

    def test_one_failing_recipe_falls_back_to_hand_typed_nutrition_and_others_are_computed(self):
        failing_name = MOCK_RECIPES[0]["name"]
        names_by_quantities = {id(r["ingredient_quantities"]): r["name"] for r in MOCK_RECIPES}

        def fake_compute(db, quantities, servings):
            name = names_by_quantities[id(quantities)]
            if name == failing_name:
                raise ValueError("base-recipe ingredient(s) not found in ingredient_nutrition: ['kale']")
            return self._computed(name)

        out = StringIO()
        with patch("database.seed_postgres.compute_from_quantities", side_effect=fake_compute), redirect_stdout(out):
            seed()

        self.assertIn(f"could not compute nutrition for '{failing_name}'", out.getvalue())
        self.assertIn("falling back to the hand-typed nutrition dict", out.getvalue())

        with self.Session() as db:
            rows = {row.name: row for row in db.query(BaseRecipe).all()}
            self.assertEqual(len(rows), len(MOCK_RECIPES))
            self.assertEqual(rows[failing_name].nutrition, MOCK_RECIPES[0]["nutrition"])
            for recipe in MOCK_RECIPES[1:]:
                self.assertEqual(rows[recipe["name"]].nutrition, self._computed(recipe["name"]))
            self.assertIsNotNone(db.query(User).filter_by(email=DEV_USER_EMAIL).first())
            self.assertGreater(db.query(RecipeIngredientImage).count(), 0)

    def test_dev_user_survives_a_later_failure(self):
        with patch("database.seed_postgres.compute_from_quantities", return_value=self._computed("x")), \
                patch("database.seed_postgres.image_path", side_effect=RuntimeError("disk gone")), \
                redirect_stdout(StringIO()):
            with self.assertRaises(RuntimeError):
                seed()

        with self.Session() as db:
            self.assertIsNotNone(db.query(User).filter_by(email=DEV_USER_EMAIL).first())
            self.assertEqual(db.query(BaseRecipe).count(), 0)


if __name__ == "__main__":
    unittest.main()
