"""DB match against ingredient_nutrition_aliases only -- never against
ingredient_nutrition.ingredient_name directly."""
from dataclasses import dataclass

from database.models import IngredientNutrition, IngredientNutritionAlias
from nutrition.text import normalize_alias


@dataclass
class MacroValues:
    calories: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None


@dataclass
class NutritionMatch:
    ingredient_nutrition_id: int
    macros: MacroValues
    source: str
    source_ref: str | None
    derivation: dict | None
    portion_grams: dict | None


def match_ingredient(db, name: str) -> NutritionMatch | None:
    normalized_input = normalize_alias(name)

    # Fetch all aliases and normalize both sides for comparison
    # (aliases in DB may not be pre-normalized)
    alias_rows = db.query(IngredientNutritionAlias).all()
    for alias_row in alias_rows:
        if normalize_alias(alias_row.alias) == normalized_input:
            row = db.get(IngredientNutrition, alias_row.ingredient_nutrition_id)
            if not row:
                return None

            return NutritionMatch(
                ingredient_nutrition_id=row.id,
                macros=MacroValues(calories=row.calories, protein_g=row.protein_g, carbs_g=row.carbs_g, fat_g=row.fat_g),
                source=row.source, source_ref=row.source_ref, derivation=row.derivation, portion_grams=row.portion_grams,
            )
    return None
