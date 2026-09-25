# backend/tests/test_nutrition_seed_inmu.py
import csv
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, IngredientNutrition, IngredientNutritionAlias
from nutrition.seed_inmu import import_csv

_HEADER = [
    "Food_Code", "Thai_Name", "English_Name", "Scientific_name",
    "SUGAR(g)", "Protein(g)", "Fat(g)", "Energy(kcal) by calculation",
    "CHOCDF (g) Carbohydrate", "FIBTG (g) Dietary fibre",
]


def _write_fixture_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(_HEADER)
        writer.writerows(rows)


class ImportCsvTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(engine)

    def tearDown(self):
        self.db.close()

    def test_row_with_all_four_macros_is_imported_as_measured(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "fixture.csv"
            _write_fixture_csv(csv_path, [["A1", "ข้าวกล้อง, พันธุ์หอมมะลิ, ดิบ", "Rice brown raw", "Oryza sativa", "0.25", "7.34", "2.95", "363", "76.8", "3.5"]])
            import_csv(self.db, str(csv_path))
        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="ข้าวกล้อง, พันธุ์หอมมะลิ, ดิบ").one()
        self.assertEqual(row.calories, 363.0)
        self.assertEqual(row.source, "INMU")
        self.assertEqual(row.source_ref, "A1")
        self.assertEqual(row.unit_basis, "100g")
        self.assertIsNone(row.derivation)

    def test_per_100ml_row_gets_100ml_unit_basis(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "fixture.csv"
            _write_fixture_csv(csv_path, [["N72", "น้ำปลา, เกรด1, ต่อ 100 มล.", "Fish sauce", "-", "-", "8.88", "0.01", "63", "-", "-"]])
            import_csv(self.db, str(csv_path))
        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="น้ำปลา, เกรด1, ต่อ 100 มล.").one()
        self.assertEqual(row.unit_basis, "100ml")

    def test_missing_energy_is_filled_via_atwater(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "fixture.csv"
            _write_fixture_csv(csv_path, [["A2", "ทดสอบพลังงาน", "Test energy", "-", "-", "10.0", "5.0", "-", "20.0", "-"]])
            import_csv(self.db, str(csv_path))
        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="ทดสอบพลังงาน").one()
        self.assertEqual(row.calories, 165.0)
        self.assertEqual(row.derivation, {"energy_kcal": "atwater"})

    def test_missing_carbs_is_filled_by_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "fixture.csv"
            _write_fixture_csv(csv_path, [["A3", "ทดสอบคาร์บ", "Test carbs", "-", "-", "7.34", "2.95", "363", "-", "-"]])
            import_csv(self.db, str(csv_path))
        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="ทดสอบคาร์บ").one()
        self.assertAlmostEqual(row.carbs_g, 76.7725, places=3)
        self.assertEqual(row.derivation, {"carbs_g": "by_difference"})

    def test_negative_by_difference_carbs_is_clamped_to_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "fixture.csv"
            _write_fixture_csv(csv_path, [["G4", "กุ้งก้ามกราม, สด", "Shrimp fresh", "-", "-", "17.9", "3.7", "88", "-", "-"]])
            import_csv(self.db, str(csv_path))
        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="กุ้งก้ามกราม, สด").one()
        self.assertEqual(row.carbs_g, 0.0)
        self.assertEqual(row.derivation, {"carbs_g": "by_difference_clamped"})

    def test_insufficient_macros_leaves_energy_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "fixture.csv"
            _write_fixture_csv(csv_path, [["A4", "ทดสอบขาดข้อมูล", "Test missing", "-", "-", "-", "5.0", "-", "-", "-"]])
            import_csv(self.db, str(csv_path))
        row = self.db.query(IngredientNutrition).filter_by(ingredient_name="ทดสอบขาดข้อมูล").one()
        self.assertIsNone(row.calories)

    def test_creates_thai_and_english_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "fixture.csv"
            _write_fixture_csv(csv_path, [["A5", "กุ้งก้ามกราม, สด", "Shrimp, fresh", "-", "-", "20.0", "1.0", "90", "0", "0"]])
            result = import_csv(self.db, str(csv_path))
        self.assertEqual(result["imported"], 1)
        aliases = {a.alias for a in self.db.query(IngredientNutritionAlias).all()}
        self.assertIn("กุ้งก้ามกราม, สด", aliases)
        self.assertIn("shrimp, fresh", aliases)

    def test_row_with_no_thai_name_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "fixture.csv"
            _write_fixture_csv(csv_path, [["A6", "", "Nameless", "-", "-", "1.0", "1.0", "10", "1.0", "0"]])
            result = import_csv(self.db, str(csv_path))
        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped_no_name"], 1)

    def test_reimport_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "fixture.csv"
            _write_fixture_csv(csv_path, [["A7", "ทดสอบซ้ำ", "Test dup", "-", "-", "1.0", "1.0", "10", "1.0", "0"]])
            import_csv(self.db, str(csv_path))
            result = import_csv(self.db, str(csv_path))
        self.assertEqual(result["imported"], 0)
        self.assertEqual(len(self.db.query(IngredientNutrition).filter_by(ingredient_name="ทดสอบซ้ำ").all()), 1)


if __name__ == "__main__":
    unittest.main()
