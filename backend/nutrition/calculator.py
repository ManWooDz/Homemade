# backend/nutrition/calculator.py
"""compute_recipe_nutrition is for generated recipes (LLM fallback
allowed). compute_from_quantities is for base recipes at seed time
(pre-parsed input, no LLM fallback, raises on any unmatched name -- see
Task 11's rev 3 notes for why silent 0 is unacceptable there).

Check order in compute_recipe_nutrition matters: a zero-nutrition
constant (salt/water) is checked BEFORE the unparsed-quantity branch, so
"เกลือเล็กน้อย" contributes 0 with no flag -- not "unparsed with a flag"."""
from dataclasses import dataclass

from nutrition.curated_aliases import ZERO_NUTRITION_CONSTANTS
from nutrition.lookup import MacroValues, match_ingredient
from nutrition.parser import parse_ingredient_string
from nutrition.text import normalize_alias
from nutrition.units import resolve_grams

_MACRO_KEYS = ("calories", "protein_g", "carbs_g", "fat_g")


@dataclass
class NutritionResult:
    nutrition: dict
    partially_estimated: bool
    partially_estimated_reasons: list[str]


def _has_deep_fry(instructions: list[str]) -> bool:
    for line in instructions:
        if "ทอด" in line.replace("ผัดทอด", "").replace("ผัด", ""):
            return True
    return False


def _add_contribution(totals: dict, macros: MacroValues, quantity_g: float) -> None:
    factor = quantity_g / 100.0
    for key in _MACRO_KEYS:
        totals[key] += (getattr(macros, key) or 0.0) * factor


def _zero_nutrition_constant(name: str) -> MacroValues | None:
    return ZERO_NUTRITION_CONSTANTS.get(normalize_alias(name))


def compute_recipe_nutrition(db, adjusted_ingredients, instructions, servings, llm_estimator) -> NutritionResult:
    totals = {key: 0.0 for key in _MACRO_KEYS}
    reasons: list[str] = []
    pending_llm_estimate: list[tuple[str, float]] = []

    for item in [parse_ingredient_string(raw) for raw in adjusted_ingredients]:
        constant = _zero_nutrition_constant(item.name)
        if constant is not None:
            # Contributes 0, no flag -- quantity/unit are irrelevant for a
            # known-zero ingredient, so no resolution is even attempted.
            continue

        if item.parse_status == "unparsed":
            reasons.append(f"quantity not determined: {item.raw}")
            continue

        match = match_ingredient(db, item.name)
        portion_grams = match.portion_grams if match else None
        quantity_g = resolve_grams(item.quantity, item.unit, portion_grams)

        if match is not None and quantity_g is not None:
            _add_contribution(totals, match.macros, quantity_g)
            continue
        if match is None and quantity_g is not None:
            pending_llm_estimate.append((item.name, quantity_g))
            continue
        reasons.append(f"quantity or ingredient not resolved: {item.raw}")

    if pending_llm_estimate:
        names = [name for name, _ in pending_llm_estimate]
        for (name, quantity_g), macros in zip(pending_llm_estimate, llm_estimator.estimate(names)):
            _add_contribution(totals, macros, quantity_g)
            reasons.append(f"LLM_ESTIMATE composition: {name}")

    if _has_deep_fry(instructions):
        reasons.append("deep-fry (ทอด): oil absorption not modeled, fat/kcal may be overcounted")

    per_serving = {key: round(totals[key] / servings, 1) for key in _MACRO_KEYS}
    return NutritionResult(
        nutrition={"basis": "per_serving", **per_serving},
        partially_estimated=len(reasons) > 0,
        partially_estimated_reasons=reasons,
    )


def compute_from_quantities(db, quantities: list[dict], servings: int) -> dict:
    totals = {key: 0.0 for key in _MACRO_KEYS}
    unmatched: list[str] = []

    for entry in quantities:
        name, quantity_g = entry["name"], entry["quantity_g"]
        constant = _zero_nutrition_constant(name)
        if constant is not None:
            _add_contribution(totals, constant, quantity_g)
            continue

        match = match_ingredient(db, name)
        if match is None:
            unmatched.append(name)
            continue
        _add_contribution(totals, match.macros, quantity_g)

    if unmatched:
        raise ValueError(
            f"base-recipe ingredient(s) not found in ingredient_nutrition: {unmatched} "
            "-- add a curated alias (nutrition/data/curated_aliases.json) or a USDA search "
            "term before seeding base recipes; silently contributing 0 here would repeat "
            "the original hand-typed-nutrition problem."
        )

    return {"basis": "per_serving", **{key: round(totals[key] / servings, 1) for key in _MACRO_KEYS}}
