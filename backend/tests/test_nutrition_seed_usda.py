import unittest
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, IngredientNutrition, IngredientNutritionAlias
from nutrition.seed_usda import backfill_portions, import_usda

_SEARCH_RESPONSE = {"foods": [{"fdcId": 12345, "description": "Shrimp, raw", "dataType": "SR Legacy"}]}

_DETAIL_RESPONSE = {
    "fdcId": 12345, "description": "Shrimp, raw",
    "foodNutrients": [
        {"nutrient": {"name": "Energy", "unitName": "KCAL"}, "amount": 85.0},
        {"nutrient": {"name": "Energy", "unitName": "kJ"}, "amount": 356.0},
        {"nutrient": {"name": "Protein", "unitName": "G"}, "amount": 20.1},
        {"nutrient": {"name": "Total lipid (fat)", "unitName": "G"}, "amount": 0.5},
        {"nutrient": {"name": "Carbohydrate, by difference", "unitName": "G"}, "amount": 0.2},
    ],
    "foodPortions": [
        {"gramWeight": 85.0, "amount": 1.0, "portionDescription": "3 oz"},
        {"gramWeight": 28.0, "amount": 1.0, "modifier": "1 large shrimp"},
    ],
}

_FISH_SAUCE_DETAIL = {
    "fdcId": 99999, "description": "Fish sauce", "foodNutrients": [],
    "foodPortions": [
        {"gramWeight": 18.0, "amount": 1.0, "portionDescription": "1 tbsp"},
        {"gramWeight": 6.0, "amount": 1.0, "portionDescription": "1 tsp"},
    ],
}


def _fake_session(search_json, detail_json):
    session = MagicMock()

    def fake_get(url, params=None, timeout=None):
        response = MagicMock()
        response.raise_for_status = lambda: None
        response.json = lambda: (search_json if "search" in url else detail_json)
        return response

    session.get.side_effect = fake_get
    return session


class ImportUsdaTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(engine)

    def tearDown(self):
        self.db.close()

    def test_imports_matched_food_using_kcal_not_kj(self):
        result = import_usda(self.db, _fake_session(_SEARCH_RESPONSE, _DETAIL_RESPONSE), "fake-key", {"shrimp": "shrimp raw"})
        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="shrimp").one()
        self.assertEqual(row.calories, 85.0)
        self.assertEqual(row.source_ref, "12345")
        self.assertEqual(result["imported"], 1)

    def test_large_shrimp_portion_is_not_treated_as_an_egg_count(self):
        import_usda(self.db, _fake_session(_SEARCH_RESPONSE, _DETAIL_RESPONSE), "fake-key", {"shrimp": "shrimp raw"})
        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="shrimp").one()
        self.assertNotIn("ฟอง", row.portion_grams or {})

    def test_skips_name_already_present_from_inmu_seeding(self):
        self.db.add(IngredientNutrition(ingredient_name="shrimp", unit_basis="100g", calories=1.0, protein_g=1.0, carbs_g=1.0, fat_g=1.0, source="INMU"))
        self.db.commit()
        result = import_usda(self.db, _fake_session(_SEARCH_RESPONSE, _DETAIL_RESPONSE), "fake-key", {"shrimp": "shrimp raw"})
        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped_existing"], 1)

    def test_no_search_results_is_skipped_not_an_error(self):
        result = import_usda(self.db, _fake_session({"foods": []}, _DETAIL_RESPONSE), "fake-key", {"nonexistent": "zzz"})
        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped_no_match"], 1)


class BackfillPortionsTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(engine)
        self.fish_sauce = IngredientNutrition(
            ingredient_name="น้ำปลา, เกรด1, ต่อ 100 มล.", unit_basis="100ml",
            calories=63.0, protein_g=8.88, carbs_g=6.85, fat_g=0.01, source="INMU", source_ref="N72",
        )
        self.db.add(self.fish_sauce)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_backfills_portion_grams_by_food_code_without_changing_macros(self):
        session = _fake_session({"foods": [{"fdcId": 99999, "dataType": "SR Legacy"}]}, _FISH_SAUCE_DETAIL)
        result = backfill_portions(self.db, session, "fake-key", {"N72": "fish sauce"})

        row = self.db.query(IngredientNutrition).filter_by(source_ref="N72").one()
        self.assertEqual(row.source, "INMU")
        self.assertEqual(row.calories, 63.0)
        self.assertEqual(row.portion_grams["ช้อนโต๊ะ"], 18.0)
        self.assertEqual(row.portion_grams["ช้อนชา"], 6.0)
        self.assertEqual(result["backfilled"], 1)


if __name__ == "__main__":
    unittest.main()
