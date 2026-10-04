import unittest
from unittest.mock import MagicMock

import requests

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, IngredientNutrition, IngredientNutritionAlias
from nutrition.seed_usda import backfill_portions, fetch_foods, import_usda

_DETAIL_RESPONSE = {
    "fdcId": 12345, "description": "Shrimp, raw",
    "foodNutrients": [
        {"nutrient": {"name": "Energy", "unitName": "kcal"}, "amount": 85.0},
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

_FOUNDATION_DETAIL = {
    **_DETAIL_RESPONSE,
    "foodNutrients": [
        {"nutrient": {"id": 2047, "name": "Energy (Atwater General Factors)", "unitName": "kcal"}, "amount": 554.602},
        {"nutrient": {"id": 2048, "name": "Energy (Atwater Specific Factors)", "unitName": "kcal"}, "amount": 514.83917},
        *_DETAIL_RESPONSE["foodNutrients"][2:],
    ],
}


def _fake_session(batch_json):
    session = MagicMock()

    def fake_get(url, params=None, timeout=None):
        response = MagicMock()
        response.raise_for_status = lambda: None
        response.json = lambda: batch_json
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
        result = import_usda(self.db, _fake_session([_DETAIL_RESPONSE]), "fake-key", {"shrimp": 12345})
        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="shrimp").one()
        self.assertEqual(row.calories, 85.0)
        self.assertEqual(row.source_ref, "12345")
        self.assertEqual(result["imported"], 1)

    def test_large_shrimp_portion_is_not_treated_as_an_egg_count(self):
        import_usda(self.db, _fake_session([_DETAIL_RESPONSE]), "fake-key", {"shrimp": 12345})
        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="shrimp").one()
        self.assertNotIn("ฟอง", row.portion_grams or {})

    def test_foundation_energy_prefers_specific_atwater_factors(self):
        import_usda(self.db, _fake_session([_FOUNDATION_DETAIL]), "fake-key", {"shrimp": 12345})
        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="shrimp").one()
        self.assertEqual(row.calories, 514.83917)

    def test_skips_name_already_present_from_inmu_seeding(self):
        self.db.add(IngredientNutrition(ingredient_name="shrimp", unit_basis="100g", calories=1.0, protein_g=1.0, carbs_g=1.0, fat_g=1.0, source="INMU"))
        self.db.commit()
        session = _fake_session([_DETAIL_RESPONSE])
        result = import_usda(self.db, session, "fake-key", {"shrimp": 12345})
        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped_existing"], 1)
        session.get.assert_not_called()

    def test_skips_name_already_covered_by_an_alias_without_calling_api(self):
        row = IngredientNutrition(ingredient_name="ไข่ไก่, ทั้งฟอง, ดิบ", unit_basis="100g", calories=1.0, protein_g=1.0, carbs_g=1.0, fat_g=1.0, source="INMU", source_ref="H19")
        self.db.add(row)
        self.db.flush()
        self.db.add(IngredientNutritionAlias(alias="egg", ingredient_nutrition_id=row.id))
        self.db.commit()
        session = _fake_session([_DETAIL_RESPONSE])

        result = import_usda(self.db, session, "fake-key", {"egg": 12345})

        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped_existing"], 1)
        session.get.assert_not_called()
        self.assertEqual(self.db.query(IngredientNutrition).count(), 1)

    def test_http_error_does_not_leak_api_key(self):
        secret = "SECRET-KEY-123"
        session = MagicMock()

        def failing_get(url, params=None, timeout=None):
            response = MagicMock()
            response.status_code = 403
            full_url = requests.Request("GET", url, params=params).prepare().url

            def raise_for_status():
                raise requests.HTTPError(f"403 Client Error: Forbidden for url: {full_url}", response=response)

            response.raise_for_status = raise_for_status
            return response

        session.get.side_effect = failing_get
        with self.assertRaises(RuntimeError) as ctx:
            fetch_foods(session, secret, [12345])

        self.assertNotIn(secret, str(ctx.exception))
        self.assertNotIn("api_key", str(ctx.exception))
        self.assertIn("batch food details", str(ctx.exception))
        self.assertIn("403", str(ctx.exception))
        self.assertIsNone(ctx.exception.__cause__)
        self.assertTrue(ctx.exception.__suppress_context__)

    def test_connection_error_does_not_leak_api_key(self):
        secret = "SECRET-KEY-123"
        session = MagicMock()
        session.get.side_effect = requests.ConnectionError(f"Max retries exceeded with url: /fdc/v1/foods/search?api_key={secret}")
        with self.assertRaises(RuntimeError) as ctx:
            fetch_foods(session, secret, [12345])
        self.assertNotIn(secret, str(ctx.exception))

    def test_missing_batch_detail_is_an_error_and_writes_nothing(self):
        with self.assertRaisesRegex(RuntimeError, "omitted requested fdcIds"):
            import_usda(self.db, _fake_session([]), "fake-key", {"shrimp": 12345})
        self.assertEqual(self.db.query(IngredientNutrition).count(), 0)

    def test_refreshes_incomplete_existing_usda_row(self):
        self.db.add(IngredientNutrition(
            ingredient_name="shrimp", unit_basis="100g", calories=None,
            protein_g=1.0, carbs_g=1.0, fat_g=1.0, source="USDA", source_ref="999",
        ))
        self.db.commit()

        result = import_usda(self.db, _fake_session([_DETAIL_RESPONSE]), "fake-key", {"shrimp": 12345})

        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="shrimp").one()
        self.assertEqual(result["refreshed"], 1)
        self.assertEqual(row.source_ref, "12345")
        self.assertEqual(row.calories, 85.0)

    def test_rejects_incomplete_macros_without_committing(self):
        incomplete = {**_DETAIL_RESPONSE, "foodNutrients": _DETAIL_RESPONSE["foodNutrients"][1:]}
        with self.assertRaisesRegex(ValueError, "missing required macros"):
            import_usda(self.db, _fake_session([incomplete]), "fake-key", {"shrimp": 12345})
        self.assertEqual(self.db.query(IngredientNutrition).count(), 0)


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
        session = _fake_session([_FISH_SAUCE_DETAIL])
        result = backfill_portions(self.db, session, "fake-key", {"N72": (99999, "fish sauce")})

        row = self.db.query(IngredientNutrition).filter_by(source_ref="N72").one()
        self.assertEqual(row.source, "INMU")
        self.assertEqual(row.calories, 63.0)
        self.assertEqual(row.portion_grams["ช้อนโต๊ะ"], 18.0)
        self.assertEqual(row.portion_grams["ช้อนชา"], 6.0)
        self.assertEqual(result["backfilled"], 1)


if __name__ == "__main__":
    unittest.main()
