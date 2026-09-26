"""Imports the full BaoWio/Thai_Nutrition_Dataset CSV (all rows, not
filtered). The aliases created here are FULL descriptive strings -- Task
8 (curated_aliases.py) adds the short names a recipe actually contains.

Usage: python nutrition/seed_inmu.py [path-to-csv]
"""
import csv
import sys

from database.db import SessionLocal
from database.models import IngredientNutrition, IngredientNutritionAlias
from nutrition.text import normalize_alias

_DEFAULT_CSV_PATH = "nutrition/data/inmu_nutrition_dataset.csv"


def _num(value: str) -> float | None:
    value = value.strip()
    return None if value in ("", "-") else float(value)


def _unit_basis(thai_name: str) -> str:
    return "100ml" if "ต่อ 100 มล." in thai_name else "100g"


def _derive_energy_and_carbs(protein, fat, carbs, energy) -> tuple:
    derivation: dict = {}
    if energy is None and protein is not None and fat is not None and carbs is not None:
        energy = 4 * protein + 4 * carbs + 9 * fat
        derivation["energy_kcal"] = "atwater"
    elif carbs is None and energy is not None and protein is not None and fat is not None:
        derived_carbs = (energy - 4 * protein - 9 * fat) / 4
        if derived_carbs < 0:
            carbs, derivation["carbs_g"] = 0.0, "by_difference_clamped"
        else:
            carbs, derivation["carbs_g"] = derived_carbs, "by_difference"
    return energy, carbs, derivation


def _add_alias_if_new(db, alias_text: str, ingredient_nutrition_id: int) -> None:
    normalized = normalize_alias(alias_text)
    if not normalized:
        return
    if db.query(IngredientNutritionAlias).filter_by(alias=normalized).first():
        return
    db.add(IngredientNutritionAlias(alias=normalized, ingredient_nutrition_id=ingredient_nutrition_id))


def import_csv(db, csv_path: str) -> dict:
    imported = 0
    skipped_no_name = 0
    negative_carbs_clamped = 0

    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            thai_name = row["Thai_Name"].strip()
            if not thai_name:
                skipped_no_name += 1
                continue
            if db.query(IngredientNutrition).filter_by(ingredient_name=thai_name).first():
                continue

            protein = _num(row["Protein(g)"])
            fat = _num(row["Fat(g)"])
            carbs = _num(row["CHOCDF (g) Carbohydrate"])
            energy = _num(row["Energy(kcal) by calculation"])
            energy, carbs, derivation = _derive_energy_and_carbs(protein, fat, carbs, energy)
            if derivation.get("carbs_g") == "by_difference_clamped":
                negative_carbs_clamped += 1

            nutrition_row = IngredientNutrition(
                ingredient_name=thai_name, unit_basis=_unit_basis(thai_name),
                calories=energy, protein_g=protein, carbs_g=carbs, fat_g=fat,
                source="INMU", source_ref=row["Food_Code"].strip(), derivation=derivation or None,
            )
            db.add(nutrition_row)
            db.flush()

            _add_alias_if_new(db, thai_name, nutrition_row.id)
            english_name = row["English_Name"].strip()
            if english_name and english_name != "-":
                _add_alias_if_new(db, english_name, nutrition_row.id)

            imported += 1

    db.commit()
    return {"imported": imported, "skipped_no_name": skipped_no_name, "negative_carbs_clamped": negative_carbs_clamped}


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_CSV_PATH
    db = SessionLocal()
    try:
        result = import_csv(db, path)
    finally:
        db.close()
    print(f"seeded: {result['imported']} rows (INMU), skipped {result['skipped_no_name']} with no name, "
          f"{result['negative_carbs_clamped']} had carbs-by-difference clamped from negative to 0")
