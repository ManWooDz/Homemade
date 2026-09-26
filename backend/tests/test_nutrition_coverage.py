import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, IngredientNutrition, IngredientNutritionAlias
from eval.nutrition_coverage import measure_match_accuracy


class MeasureMatchAccuracyTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(engine)
        shrimp = IngredientNutrition(ingredient_name="กุ้งก้ามกราม, สด", unit_basis="100g", calories=88.0, protein_g=17.9, carbs_g=0.0, fat_g=3.7, source="INMU", source_ref="G4")
        self.db.add(shrimp)
        self.db.flush()
        self.db.add(IngredientNutritionAlias(alias="กุ้ง", ingredient_nutrition_id=shrimp.id))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_reports_name_accuracy_over_all_cases_and_grounding_over_expected_positives_only(self):
        cases = [
            {"raw": "กุ้ง 200 กรัม", "expected_name": "กุ้ง", "expected_quantity_g": 200.0, "expected_in_db": True, "expected_source_ref": "G4"},
            {"raw": "มังกรบิน 100 กรัม", "expected_name": "มังกรบิน", "expected_quantity_g": 100.0, "expected_in_db": False, "expected_source_ref": None},
        ]
        result = measure_match_accuracy(self.db, cases)

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["name_correct"], 2)  # both parse to the exact expected name
        self.assertEqual(result["expected_in_db_count"], 1)
        self.assertEqual(result["row_correct"], 1)
        self.assertEqual(result["quantity_resolved"], 1)
        self.assertEqual(result["fully_grounded"], 1)
        self.assertEqual(result["match_accuracy"], 1.0)
        self.assertEqual(result["coverage_rate"], 1.0)

    def test_a_match_to_the_wrong_row_is_not_counted_as_correct(self):
        cases = [{"raw": "กุ้ง 200 กรัม", "expected_name": "กุ้ง", "expected_quantity_g": 200.0, "expected_in_db": True, "expected_source_ref": "G8"}]
        result = measure_match_accuracy(self.db, cases)
        self.assertEqual(result["row_correct"], 0)
        self.assertEqual(result["fully_grounded"], 0)

    def test_wrong_quantity_expectation_is_not_counted_as_fully_grounded(self):
        cases = [{"raw": "กุ้ง 200 กรัม", "expected_name": "กุ้ง", "expected_quantity_g": 999.0, "expected_in_db": True, "expected_source_ref": "G4"}]
        result = measure_match_accuracy(self.db, cases)
        self.assertEqual(result["row_correct"], 1)  # row identity is still right
        self.assertEqual(result["fully_grounded"], 0)  # but the parsed quantity doesn't match what was expected


if __name__ == "__main__":
    unittest.main()
