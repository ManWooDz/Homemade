"""import_usda: full macros for used English names not covered by INMU.
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

_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
_DETAIL_URL = "https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
_PREFERRED_DATA_TYPES = "SR Legacy,Foundation"

# Every unique ingredient name across seed_postgres.py's MOCK_RECIPES,
# enumerated directly from that file.
USDA_SEARCH_TERMS: dict[str, str] = {
    "kale": "kale raw", "quinoa": "quinoa cooked", "avocado": "avocado raw",
    "cherry tomatoes": "tomatoes cherry raw", "pumpkin seeds": "pumpkin seeds raw",
    "spinach": "spinach raw", "cucumber": "cucumber raw", "bell pepper": "peppers sweet raw",
    "red onion": "onions red raw", "feta cheese": "cheese feta",
    "balsamic vinaigrette": "balsamic vinaigrette dressing", "purple cabbage": "cabbage red raw",
    "carrot": "carrots raw", "edamame": "edamame cooked",
    "yellow bell pepper": "peppers sweet yellow raw", "sesame dressing": "sesame dressing",
    "ramen noodles": "noodles ramen", "pork belly (chashu)": "pork belly raw",
    "tonkotsu broth": "pork bone broth", "soft-boiled egg": "egg whole cooked",
    "green onion": "onions spring or scallions raw", "nori seaweed": "seaweed nori dried",
    "soy sauce": "soy sauce", "rice noodles": "noodles rice cooked", "shrimp": "shrimp raw",
    "egg": "egg whole raw", "bean sprouts": "bean sprouts raw", "chives": "chives raw",
    "tofu": "tofu raw", "tamarind paste": "tamarind raw", "fish sauce": "fish sauce",
    "palm sugar": "sugars palm", "peanuts": "peanuts raw", "minced pork": "pork ground raw",
    "holy basil leaves": "basil raw", "garlic": "garlic raw",
    "bird's eye chilies": "peppers hot chili raw", "oyster sauce": "oyster sauce",
    "sugar": "sugars granulated", "vegetable oil": "vegetable oil",
    "kalamata olives": "olives kalamata", "olive oil": "olive oil", "oregano": "oregano dried",
    "beef steak": "beef steak raw", "rosemary": "rosemary dried", "butter": "butter salted",
    "black pepper": "pepper black", "salt": "salt table", "lemongrass": "lemongrass raw",
    "galangal": "galangal raw", "kaffir lime leaves": "kaffir lime leaves",
    "lime juice": "lime juice raw", "mushrooms": "mushrooms raw", "cilantro": "cilantro raw",
    "chili paste": "chili paste",
}

# Keyed by Food_Code (source_ref), not the Thai name string -- only
# foodPortions are fetched, never the macros. Real Food_Codes from Task 5.
USDA_PORTION_BACKFILL: dict[str, str] = {
    "N72": "fish sauce",       # น้ำปลา, เกรด1
    "N134": "soy sauce",       # ซีอิ๊วขาว, สูตร 1
    "K41": "soybean oil",      # น้ำมันถั่วเหลือง (generic vegetable-oil proxy)
}

_EGG_SEARCH_TERM_MARKERS = ("egg",)


def _extract_nutrient(detail: dict, nutrient_name: str) -> float | None:
    for entry in detail.get("foodNutrients", []):
        nutrient = entry.get("nutrient", {})
        if nutrient.get("name") != nutrient_name:
            continue
        if nutrient_name == "Energy" and nutrient.get("unitName") != "KCAL":
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


def _get_json_sanitized(session, url: str, params: dict, what: str) -> dict:
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


def fetch_food(session, api_key: str, query: str) -> dict | None:
    search_json = _get_json_sanitized(
        session, _SEARCH_URL,
        {"query": query, "dataType": _PREFERRED_DATA_TYPES, "pageSize": 1, "api_key": api_key},
        f"search query {query!r}",
    )
    foods = search_json.get("foods", [])
    if not foods:
        return None
    fdc_id = foods[0]["fdcId"]
    return _get_json_sanitized(
        session, _DETAIL_URL.format(fdc_id=fdc_id), {"api_key": api_key},
        f"food detail fdcId={fdc_id} (query {query!r})",
    )


def import_usda(db, session, api_key: str, search_terms: dict[str, str]) -> dict:
    imported = skipped_existing = skipped_no_match = 0

    for ingredient_name, query in search_terms.items():
        # Skip if the exact name exists OR the name already resolves through
        # the alias table (e.g. an INMU curated alias) -- otherwise we'd
        # spend an API call and insert a duplicate row for a covered name.
        if (
            db.query(IngredientNutrition).filter_by(ingredient_name=ingredient_name).first()
            or match_ingredient(db, ingredient_name) is not None
        ):
            skipped_existing += 1
            continue

        detail = fetch_food(session, api_key, query)
        if not detail:
            skipped_no_match += 1
            continue

        print(f"  USDA match: '{ingredient_name}' -> '{detail.get('description')}' (fdcId={detail['fdcId']}) -- review this")

        nutrition_row = IngredientNutrition(
            ingredient_name=ingredient_name, unit_basis="100g",
            calories=_extract_nutrient(detail, "Energy"), protein_g=_extract_nutrient(detail, "Protein"),
            carbs_g=_extract_nutrient(detail, "Carbohydrate, by difference"), fat_g=_extract_nutrient(detail, "Total lipid (fat)"),
            source="USDA", source_ref=str(detail["fdcId"]), portion_grams=_extract_portion_grams(detail, query) or None,
        )
        db.add(nutrition_row)
        db.flush()

        normalized = normalize_alias(ingredient_name)
        if not db.query(IngredientNutritionAlias).filter_by(alias=normalized).first():
            db.add(IngredientNutritionAlias(alias=normalized, ingredient_nutrition_id=nutrition_row.id))

        imported += 1

    db.commit()
    return {"imported": imported, "skipped_existing": skipped_existing, "skipped_no_match": skipped_no_match}


def backfill_portions(db, session, api_key: str, portion_terms: dict[str, str]) -> dict:
    backfilled = skipped_row_not_found = 0

    for food_code, query in portion_terms.items():
        row = db.query(IngredientNutrition).filter_by(source_ref=food_code).first()
        if not row:
            skipped_row_not_found += 1
            continue

        detail = fetch_food(session, api_key, query)
        if not detail:
            continue

        portions = _extract_portion_grams(detail, query)
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
        import_result = import_usda(db, session, api_key, USDA_SEARCH_TERMS)
        backfill_result = backfill_portions(db, session, api_key, USDA_PORTION_BACKFILL)
    finally:
        db.close()
    print(f"seeded: {import_result['imported']} rows (USDA), {import_result['skipped_existing']} already covered, "
          f"{import_result['skipped_no_match']} had no match; portion backfill: {backfill_result['backfilled']} rows updated")
