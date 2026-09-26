import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, IngredientNutrition, IngredientNutritionAlias
from nutrition.curated_aliases import ZERO_NUTRITION_CONSTANTS, apply_curated_aliases
from nutrition.text import normalize_alias


class ApplyCuratedAliasesTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(engine)
        self.shrimp = IngredientNutrition(ingredient_name="กุ้งก้ามกราม, สด", unit_basis="100g", calories=88.0, protein_g=17.9, carbs_g=0.0, fat_g=3.7, source="INMU", source_ref="G4")
        self.db.add(self.shrimp)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_applies_curated_alias_to_matching_food_code(self):
        result = apply_curated_aliases(self.db, [{"alias": "กุ้ง", "food_code": "G4", "note": "test"}])
        self.assertEqual(result["applied"], 1)
        alias_row = self.db.query(IngredientNutritionAlias).filter_by(alias="กุ้ง").one()
        self.assertEqual(alias_row.ingredient_nutrition_id, self.shrimp.id)

    def test_skips_entry_whose_food_code_was_never_imported(self):
        result = apply_curated_aliases(self.db, [{"alias": "หมูสับ", "food_code": "ZZZ999", "note": "not imported"}])
        self.assertEqual(result["applied"], 0)
        self.assertEqual(result["skipped_missing_row"], 1)

    def test_curated_portion_grams_merge_onto_row_without_touching_other_fields(self):
        self.shrimp.portion_grams = {"ตัว": 15.0, "ถ้วย": 140.0}
        self.db.commit()

        result = apply_curated_aliases(
            self.db,
            [{"alias": "กุ้ง", "food_code": "G4", "note": "test", "portion_grams": {"ถ้วย": 150.0, "ขีด": 100.0}}],
        )

        self.assertEqual(result["applied"], 1)
        self.db.expire_all()
        row = self.db.query(IngredientNutrition).filter_by(source_ref="G4").one()
        self.assertEqual(row.portion_grams, {"ตัว": 15.0, "ถ้วย": 150.0, "ขีด": 100.0})
        self.assertEqual((row.calories, row.protein_g, row.carbs_g, row.fat_g), (88.0, 17.9, 0.0, 3.7))
        self.assertEqual((row.source, row.source_ref, row.ingredient_name), ("INMU", "G4", "กุ้งก้ามกราม, สด"))

    def test_curated_portion_grams_on_row_with_no_prior_portions(self):
        apply_curated_aliases(self.db, [{"alias": "กุ้ง", "food_code": "G4", "note": "t", "portion_grams": {"ตัว": 15.0}}])
        self.db.expire_all()
        self.assertEqual(self.db.query(IngredientNutrition).filter_by(source_ref="G4").one().portion_grams, {"ตัว": 15.0})

    def test_shipped_curated_json_parses_and_portion_grams_are_numeric(self):
        import json
        import os

        path = os.path.join(os.path.dirname(__file__), "..", "nutrition", "data", "curated_aliases.json")
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)
        by_alias = {e["alias"]: e for e in entries}
        self.assertEqual(by_alias["ไข่ไก่"]["portion_grams"], {"ฟอง": 50.0})
        self.assertEqual(by_alias["น้ำตาล"]["portion_grams"], {"ช้อนโต๊ะ": 15.0})

    def test_zero_nutrition_constants_use_normalized_keys(self):
        # (rev 3) Regression test for the exact bug found: a raw literal
        # key containing SARA AM would never match its own normalized form.
        self.assertIn(normalize_alias("เกลือ"), ZERO_NUTRITION_CONSTANTS)
        self.assertIn(normalize_alias("น้ำเปล่า"), ZERO_NUTRITION_CONSTANTS)
        self.assertEqual(ZERO_NUTRITION_CONSTANTS[normalize_alias("เกลือ")].calories, 0.0)


if __name__ == "__main__":
    unittest.main()
