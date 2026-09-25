import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, IngredientNutrition, IngredientNutritionAlias
from nutrition.lookup import match_ingredient


class MatchIngredientTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(engine)
        self.shrimp = IngredientNutrition(
            ingredient_name="กุ้งก้ามกราม, สด", unit_basis="100g",
            calories=88.0, protein_g=17.9, carbs_g=0.0, fat_g=3.7, source="INMU", source_ref="G4",
        )
        self.db.add(self.shrimp)
        self.db.flush()
        self.db.add(IngredientNutritionAlias(alias="กุ้งก้ามกราม, สด", ingredient_nutrition_id=self.shrimp.id))
        self.db.add(IngredientNutritionAlias(alias="กุ้ง", ingredient_nutrition_id=self.shrimp.id))
        self.db.add(IngredientNutritionAlias(alias="shrimp, fresh", ingredient_nutrition_id=self.shrimp.id))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_matches_short_curated_alias_not_the_full_descriptive_name(self):
        result = match_ingredient(self.db, "กุ้ง")
        self.assertIsNotNone(result)
        self.assertEqual(result.macros.calories, 88.0)
        self.assertEqual(result.source_ref, "G4")

    def test_matches_english_alias_case_insensitively(self):
        self.assertIsNotNone(match_ingredient(self.db, "Shrimp, Fresh"))

    def test_matches_thai_combining_mark_variant(self):
        water = IngredientNutrition(ingredient_name="น้ำเปล่า", unit_basis="100g", calories=0.0, protein_g=0.0, carbs_g=0.0, fat_g=0.0, source="INMU")
        self.db.add(water)
        self.db.flush()
        self.db.add(IngredientNutritionAlias(alias="น้ำเปล่า", ingredient_nutrition_id=water.id))
        self.db.commit()
        result = match_ingredient(self.db, "นํ้าเปล่า")
        self.assertIsNotNone(result)
        self.assertEqual(result.ingredient_nutrition_id, water.id)

    def test_unmatched_name_returns_none(self):
        self.assertIsNone(match_ingredient(self.db, "ยูนิคอร์นฮอร์น"))


if __name__ == "__main__":
    unittest.main()
