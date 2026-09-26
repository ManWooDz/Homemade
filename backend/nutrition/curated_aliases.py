"""Adds short, commonly-used recipe-ingredient aliases pointing at a
deliberately chosen ingredient_nutrition row (by Food_Code/fdcId).
ZERO_NUTRITION_CONSTANTS is keyed by normalize_alias(name) -- built that
way here, not with raw literals, because calculator.py looks these up via
normalize_alias() too (a raw literal key with unnormalized Thai text would
never match).

Usage: python nutrition/curated_aliases.py [path-to-json] (run AFTER
seed_usda.py -- one entry needs a real USDA fdcId, see data/curated_aliases.json)
"""
import json
import sys

from database.db import SessionLocal
from database.models import IngredientNutrition, IngredientNutritionAlias
from nutrition.lookup import MacroValues
from nutrition.text import normalize_alias

_DEFAULT_JSON_PATH = "nutrition/data/curated_aliases.json"

_RAW_ZERO_NUTRITION_CONSTANTS = {
    "เกลือ": MacroValues(calories=0.0, protein_g=0.0, carbs_g=0.0, fat_g=0.0),
    "น้ำเปล่า": MacroValues(calories=0.0, protein_g=0.0, carbs_g=0.0, fat_g=0.0),
    "น้ำแข็ง": MacroValues(calories=0.0, protein_g=0.0, carbs_g=0.0, fat_g=0.0),
}
ZERO_NUTRITION_CONSTANTS: dict[str, MacroValues] = {
    normalize_alias(name): value for name, value in _RAW_ZERO_NUTRITION_CONSTANTS.items()
}


def apply_curated_aliases(db, entries: list[dict]) -> dict:
    applied = 0
    skipped_missing_row = 0

    for entry in entries:
        row = db.query(IngredientNutrition).filter_by(source_ref=entry["food_code"]).first()
        if not row:
            skipped_missing_row += 1
            continue

        normalized = normalize_alias(entry["alias"])
        existing = db.query(IngredientNutritionAlias).filter_by(alias=normalized).first()
        if existing:
            existing.ingredient_nutrition_id = row.id
        else:
            db.add(IngredientNutritionAlias(alias=normalized, ingredient_nutrition_id=row.id))
        if "portion_grams" in entry:
            # Curated, ingredient-specific unit weights (e.g. 1 ฟอง egg ~ 50 g).
            # Merged -- never replaces -- whatever portions the row already
            # has (e.g. from seed_usda.py's backfill_portions); a curated
            # value for the same unit key wins. Reassigned as a new dict so
            # SQLAlchemy sees the JSON column change.
            row.portion_grams = {**(row.portion_grams or {}), **entry["portion_grams"]}
        applied += 1

    db.commit()
    return {"applied": applied, "skipped_missing_row": skipped_missing_row}


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_JSON_PATH
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)

    db = SessionLocal()
    try:
        result = apply_curated_aliases(db, entries)
    finally:
        db.close()
    print(f"curated aliases: {result['applied']} applied, {result['skipped_missing_row']} skipped (Food_Code not found)")
