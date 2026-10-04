"""import_usda: full macros for used English names not covered by INMU.
The FDC IDs are pinned after reviewing real USDA search results so a future
search-ranking change cannot silently map an ingredient to a different food.

backfill_portions: ONLY foodPortions merged onto an EXISTING INMU-sourced
row (found by Food_Code/source_ref, never by name -- avoids a
combining-mark mismatch), never touching that row's macros/source.

Usage: python nutrition/seed_usda.py (USDA_API_KEY set)
"""
import os

import requests
from dotenv import load_dotenv

from database.db import SessionLocal
from database.models import IngredientNutrition, IngredientNutritionAlias
from nutrition.lookup import match_ingredient
from nutrition.text import normalize_alias

load_dotenv()

_BATCH_DETAIL_URL = "https://api.nal.usda.gov/fdc/v1/foods"
_BATCH_SIZE = 20

# Every English ingredient name not already covered by INMU, pinned to a
# reviewed FoodData Central record. Lemongrass is intentionally absent because
# the INMU import already resolves it. See USDA_PROXY_NOTES for approximations.
USDA_FDC_IDS: dict[str, int] = {
    "kale": 168421, "quinoa": 168917, "avocado": 171706,
    "cherry tomatoes": 321360, "pumpkin seeds": 2515380,
    "spinach": 168462, "cucumber": 169225, "bell pepper": 170427,
    "red onion": 790577, "feta cheese": 173420,
    "balsamic vinaigrette": 2102544, "purple cabbage": 2346408,
    "carrot": 170393, "edamame": 168411,
    "yellow bell pepper": 169383, "sesame dressing": 171006,
    "ramen noodles": 171177, "pork belly (chashu)": 167812,
    "tonkotsu broth": 2707132, "soft-boiled egg": 173424,
    "green onion": 170005, "nori seaweed": 1662188,
    "soy sauce": 174278, "rice noodles": 168914, "shrimp": 175179,
    "egg": 171287, "bean sprouts": 169957, "chives": 169994,
    "tofu": 172475, "tamarind paste": 2174116, "fish sauce": 174531,
    "palm sugar": 2033749, "peanuts": 2515376, "minced pork": 2514745,
    "holy basil leaves": 172232, "garlic": 1104647,
    "bird's eye chilies": 170497, "oyster sauce": 174529,
    "sugar": 746784, "vegetable oil": 172370,
    "kalamata olives": 2063184, "olive oil": 171413, "oregano": 171328,
    "beef steak": 2727573, "rosemary": 171333, "butter": 173410,
    "black pepper": 170931, "salt": 173468,
    "galangal": 169231, "kaffir lime leaves": 167749,
    "lime juice": 168156, "mushrooms": 169251, "cilantro": 169997,
    "chili paste": 2709744,
}

USDA_PROXY_NOTES: dict[str, str] = {
    "cherry tomatoes": "grape tomatoes, raw",
    "tonkotsu broth": "generic soup broth",
    "soft-boiled egg": "hard-boiled whole egg",
    "holy basil leaves": "fresh basil",
    "galangal": "raw ginger root",
    "kaffir lime leaves": "raw lemon peel",
    "chili paste": "hot Thai sauce",
}

# Keyed by the INMU Food_Code/source_ref. Values are (FDC ID, search marker)
# and are used only for foodPortions; the INMU row's macros/source never change.
USDA_PORTION_FDC_IDS: dict[str, tuple[int, str]] = {
    "N72": (174531, "fish sauce"),       # น้ำปลา, เกรด1
    "N134": (174278, "soy sauce"),       # ซีอิ๊วขาว, สูตร 1
    "K41": (172370, "soybean oil"),      # น้ำมันถั่วเหลือง
}

_EGG_SEARCH_TERM_MARKERS = ("egg",)


def _extract_nutrient(detail: dict, nutrient_name: str) -> float | None:
    if nutrient_name == "Energy":
        kcal_entries = [
            entry for entry in detail.get("foodNutrients", [])
            if str(entry.get("nutrient", {}).get("unitName", "")).upper() == "KCAL"
        ]
        # 1008 is the traditional Energy field. Foundation foods may instead
        # expose calculated energy as 2048 (food-specific Atwater factors) and
        # 2047 (general factors); prefer the more specific calculation.
        for nutrient_id in (1008, 2048, 2047):
            for entry in kcal_entries:
                if entry.get("nutrient", {}).get("id") == nutrient_id:
                    return entry.get("amount")
        for entry in kcal_entries:
            if entry.get("nutrient", {}).get("name") == "Energy":
                return entry.get("amount")
        return None

    for entry in detail.get("foodNutrients", []):
        nutrient = entry.get("nutrient", {})
        if nutrient.get("name") != nutrient_name:
            continue
        return entry.get("amount")
    return None


def _extract_portion_grams(detail: dict, search_term: str) -> dict[str, float]:
    is_egg = any(marker in search_term.lower() for marker in _EGG_SEARCH_TERM_MARKERS)
    portions: dict[str, float] = {}
    for portion in detail.get("foodPortions", []):
        gram_weight = portion.get("gramWeight")
        amount = portion.get("amount") or 1.0
        description = (portion.get("portionDescription") or portion.get("modifier") or "").lower()
        if gram_weight is None or amount == 0:
            continue
        grams_per_unit = gram_weight / amount

        if "tablespoon" in description or "tbsp" in description:
            portions["ช้อนโต๊ะ"] = grams_per_unit
        elif "teaspoon" in description or "tsp" in description:
            portions["ช้อนชา"] = grams_per_unit
        elif "cup" in description:
            portions["ถ้วย"] = grams_per_unit
        elif is_egg and "large" in description:
            portions["ฟอง"] = grams_per_unit
    return portions


def _get_json_sanitized(session, url: str, params: dict, what: str) -> dict | list:
    """requests' exceptions (HTTPError, ConnectionError, ...) embed the full
    request URL -- including the api_key query param -- in their message.
    Re-raise as a RuntimeError carrying only a key-free description, and
    'from None' so the original (URL-bearing) exception is not chained into
    the traceback either."""
    try:
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        status_text = f" (HTTP {status})" if status is not None else ""
        raise RuntimeError(f"USDA API request failed for {what}{status_text}: {type(exc).__name__}") from None
    return response.json()


def fetch_foods(session, api_key: str, fdc_ids: list[int]) -> dict[int, dict]:
    """Fetch full FoodData Central records in deterministic batches of 20."""
    details: dict[int, dict] = {}
    unique_ids = list(dict.fromkeys(fdc_ids))
    for start in range(0, len(unique_ids), _BATCH_SIZE):
        chunk = unique_ids[start:start + _BATCH_SIZE]
        payload = _get_json_sanitized(
            session,
            _BATCH_DETAIL_URL,
            {"fdcIds": ",".join(map(str, chunk)), "format": "full", "api_key": api_key},
            f"batch food details ({len(chunk)} ids)",
        )
        if not isinstance(payload, list):
            raise RuntimeError("USDA API returned a non-list batch response")
        for detail in payload:
            if detail.get("fdcId") is not None:
                details[int(detail["fdcId"])] = detail

    missing = [fdc_id for fdc_id in unique_ids if fdc_id not in details]
    if missing:
        raise RuntimeError(f"USDA API omitted requested fdcIds: {missing}")
    return details


def _required_macros(detail: dict) -> dict[str, float]:
    macros = {
        "calories": _extract_nutrient(detail, "Energy"),
        "protein_g": _extract_nutrient(detail, "Protein"),
        "carbs_g": _extract_nutrient(detail, "Carbohydrate, by difference"),
        "fat_g": _extract_nutrient(detail, "Total lipid (fat)"),
    }
    missing = [name for name, value in macros.items() if value is None]
    if missing:
        raise ValueError(f"USDA fdcId={detail.get('fdcId')} missing required macros: {missing}")
    negative = [name for name, value in macros.items() if value < 0]
    if negative:
        raise ValueError(f"USDA fdcId={detail.get('fdcId')} has negative macros: {negative}")
    return macros


def _row_is_current(row: IngredientNutrition, fdc_id: int) -> bool:
    values = (row.calories, row.protein_g, row.carbs_g, row.fat_g)
    return row.source == "USDA" and row.source_ref == str(fdc_id) and all(
        value is not None and value >= 0 for value in values
    )


def import_usda(db, session, api_key: str, food_ids: dict[str, int]) -> dict:
    imported = refreshed = skipped_existing = 0
    pending: list[tuple[str, int, IngredientNutrition | None]] = []

    for ingredient_name, fdc_id in food_ids.items():
        existing = db.query(IngredientNutrition).filter_by(ingredient_name=ingredient_name).first()
        if existing:
            if _row_is_current(existing, fdc_id):
                skipped_existing += 1
            elif existing.source == "USDA":
                pending.append((ingredient_name, fdc_id, existing))
            else:
                skipped_existing += 1
            continue

        # An INMU alias takes precedence over adding a duplicate USDA row.
        if match_ingredient(db, ingredient_name) is not None:
            skipped_existing += 1
            continue
        pending.append((ingredient_name, fdc_id, None))

    details = fetch_foods(session, api_key, [fdc_id for _, fdc_id, _ in pending])
    prepared: list[tuple[str, int, IngredientNutrition | None, dict, dict[str, float]]] = []
    for ingredient_name, fdc_id, existing in pending:
        detail = details[fdc_id]
        prepared.append((ingredient_name, fdc_id, existing, detail, _required_macros(detail)))

    for ingredient_name, fdc_id, existing, detail, macros in prepared:
        print(f"  USDA pinned: '{ingredient_name}' -> '{detail.get('description')}' (fdcId={fdc_id})")
        derivation = {"usda_description": detail.get("description")}
        if ingredient_name in USDA_PROXY_NOTES:
            derivation["proxy"] = USDA_PROXY_NOTES[ingredient_name]

        if existing is None:
            nutrition_row = IngredientNutrition(ingredient_name=ingredient_name, unit_basis="100g")
            db.add(nutrition_row)
            imported += 1
        else:
            nutrition_row = existing
            refreshed += 1

        nutrition_row.calories = macros["calories"]
        nutrition_row.protein_g = macros["protein_g"]
        nutrition_row.carbs_g = macros["carbs_g"]
        nutrition_row.fat_g = macros["fat_g"]
        nutrition_row.source = "USDA"
        nutrition_row.source_ref = str(fdc_id)
        nutrition_row.portion_grams = _extract_portion_grams(detail, ingredient_name) or None
        nutrition_row.derivation = derivation
        db.flush()

        normalized = normalize_alias(ingredient_name)
        alias = db.query(IngredientNutritionAlias).filter_by(alias=normalized).first()
        if alias is None:
            db.add(IngredientNutritionAlias(alias=normalized, ingredient_nutrition_id=nutrition_row.id))
        else:
            alias.ingredient_nutrition_id = nutrition_row.id

    db.commit()
    return {"imported": imported, "refreshed": refreshed, "skipped_existing": skipped_existing}


def backfill_portions(db, session, api_key: str, portion_sources: dict[str, tuple[int, str]]) -> dict:
    backfilled = skipped_row_not_found = 0
    rows_and_sources = []
    for food_code, (fdc_id, marker) in portion_sources.items():
        row = db.query(IngredientNutrition).filter_by(source_ref=food_code).first()
        if not row:
            skipped_row_not_found += 1
            continue
        rows_and_sources.append((row, fdc_id, marker))

    details = fetch_foods(session, api_key, [fdc_id for _, fdc_id, _ in rows_and_sources])
    for row, fdc_id, marker in rows_and_sources:
        portions = _extract_portion_grams(details[fdc_id], marker)
        if portions:
            row.portion_grams = {**(row.portion_grams or {}), **portions}
            backfilled += 1

    db.commit()
    return {"backfilled": backfilled, "skipped_row_not_found": skipped_row_not_found}


if __name__ == "__main__":
    api_key = os.getenv("USDA_API_KEY")
    if not api_key:
        raise SystemExit("USDA_API_KEY not set — see backend/.env")

    db = SessionLocal()
    session = requests.Session()
    try:
        import_result = import_usda(db, session, api_key, USDA_FDC_IDS)
        backfill_result = backfill_portions(db, session, api_key, USDA_PORTION_FDC_IDS)
    finally:
        db.close()
    print(f"seeded: {import_result['imported']} inserted, {import_result['refreshed']} refreshed (USDA), "
          f"{import_result['skipped_existing']} already current/covered; "
          f"portion backfill: {backfill_result['backfilled']} rows updated")
