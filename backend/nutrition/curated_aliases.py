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
from nutrition.evidence import has_reviewed_metadata
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
    planned_owners = {}
    planned_portions = {}
    prepared = []

    for entry in entries:
        rows = db.query(IngredientNutrition).filter_by(source_ref=entry["food_code"]).all()
        if len(rows) > 1:
            raise ValueError(f"Curated aliases have ambiguous food code: {entry['food_code']}")
        if not rows:
            skipped_missing_row += 1
            continue
        row = rows[0]

        normalized = normalize_alias(entry["alias"])
        if normalized not in planned_owners:
            existing = db.query(IngredientNutritionAlias).filter_by(alias=normalized).first()
            planned_owners[normalized] = db.get(IngredientNutrition, existing.ingredient_nutrition_id) if existing else None
        owner = planned_owners[normalized]
        if owner is not None and owner.id != row.id and (has_reviewed_metadata(owner) or has_reviewed_metadata(row)):
            raise ValueError(f"Curated alias remap involves protected nutrition rows id={owner.id}/{row.id}; review required")
        planned_owners[normalized] = row

        merged = None
        if "portion_grams" in entry:
            merged = {**planned_portions.get(row.id, row.portion_grams or {}), **entry["portion_grams"]}
            if has_reviewed_metadata(row) and merged != (row.portion_grams or {}):
                raise ValueError(f"Curated portions cannot modify protected nutrition row id={row.id}; review required")
            planned_portions[row.id] = merged
        prepared.append((row, normalized, merged))

    for normalized, row in planned_owners.items():
        existing = db.query(IngredientNutritionAlias).filter_by(alias=normalized).first()
        if existing:
            existing.ingredient_nutrition_id = row.id
        else:
            db.add(IngredientNutritionAlias(alias=normalized, ingredient_nutrition_id=row.id))

    for row, _, merged in prepared:
        if merged is not None and not has_reviewed_metadata(row):
            # Curated, ingredient-specific unit weights (e.g. 1 ฟอง egg ~ 50 g).
            # Merged -- never replaces -- whatever portions the row already
            # has (e.g. from seed_usda.py's backfill_portions); a curated
            # value for the same unit key wins. Reassigned as a new dict so
            # SQLAlchemy sees the JSON column change.
            row.portion_grams = merged
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
