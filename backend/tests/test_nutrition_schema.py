import unittest

from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import Session

from database.models import BaseRecipe, IngredientNutrition, IngredientNutritionAlias


class NutritionSchemaTests(unittest.TestCase):
    def test_ingredient_nutrition_has_new_columns(self):
        columns = IngredientNutrition.__table__.columns
        self.assertIn("source_ref", columns)
        self.assertIn("portion_grams", columns)
        self.assertIn("derivation", columns)

    def test_ingredient_nutrition_alias_table_shape(self):
        columns = IngredientNutritionAlias.__table__.columns
        self.assertIn("alias", columns)
        self.assertIn("ingredient_nutrition_id", columns)
        fk_targets = {fk.target_fullname for fk in IngredientNutritionAlias.__table__.foreign_keys}
        self.assertIn("ingredient_nutrition.id", fk_targets)

    def test_base_recipe_has_servings_and_quantities_as_plain_json(self):
        columns = BaseRecipe.__table__.columns
        self.assertIn("servings", columns)
        self.assertIn("ingredient_quantities", columns)
        # (rev 3) BaseRecipe itself can't be created on SQLite -- it has
        # PRE-EXISTING JSONB columns (tags/ingredients/nutrition/
        # instructions) unrelated to this task. Checking the type object
        # directly, without creating the table, is what actually proves
        # this specific new column is plain JSON.
        self.assertIs(type(columns["ingredient_quantities"].type), JSON)

    def test_new_json_columns_create_on_sqlite(self):
        # Only the two BRAND-NEW tables -- proves JSON (not JSONB) was
        # used for their columns, without touching BaseRecipe's unrelated
        # existing JSONB columns.
        engine = create_engine("sqlite:///:memory:")
        IngredientNutrition.__table__.create(engine)
        IngredientNutritionAlias.__table__.create(engine)
        db = Session(engine)
        row = IngredientNutrition(
            ingredient_name="test", derivation={"energy_kcal": "atwater"},
            portion_grams={"ช้อนโต๊ะ": 15.0},
        )
        db.add(row)
        db.commit()
        fetched = db.query(IngredientNutrition).filter_by(ingredient_name="test").one()
        self.assertEqual(fetched.derivation, {"energy_kcal": "atwater"})


if __name__ == "__main__":
    unittest.main()
