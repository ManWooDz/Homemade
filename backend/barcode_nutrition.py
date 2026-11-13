"""Fetch source-labelled product nutrition and calculate compatible label contributions."""

import json
import re
from math import isclose
from pathlib import Path
from urllib.parse import urlsplit

import requests

from nutrition.units import is_nonnegative_finite, resolve_product_quantity

_OFF_ORIGIN = "https://world.openfoodfacts.org"
_LABEL_SOURCES = ("packaging", "manufacturer")
_MACRO_KEYS = ("calories", "protein_g", "carbs_g", "fat_g")
_PRODUCT_CONVERSIONS_PATH = Path(__file__).with_name("nutrition") / "product_unit_conversions.json"


class BarcodeNutritionLookupError(ValueError):
    """A product could not be identified from the provider response."""


def _normalized_barcode(code):
    if not isinstance(code, str) or not re.fullmatch(r"[0-9]{8,14}", code.strip()):
        return None
    digits = code.strip().lstrip("0")
    return digits.zfill(8 if len(digits) <= 8 else 13)


def _label_basis(label):
    per = label.get("per")
    if per in ("100g", "100ml"):
        expected_unit = per[3:]
        basis = resolve_product_quantity(label.get("per_quantity", 100), label.get("per_unit", expected_unit))
        if basis != (100, expected_unit):
            return None
    elif per == "serving":
        basis = resolve_product_quantity(label.get("per_quantity"), label.get("per_unit"))
    else:
        return None
    if basis is not None and basis[0] > 0:
        return {"quantity": basis[0], "unit": basis[1]}
    return None


def _label_nutrient(nutrients, key, *, energy=False):
    nutrient = nutrients.get(key)
    if not isinstance(nutrient, dict) or nutrient.get("modifier"):
        return None
    value, unit = nutrient.get("value"), nutrient.get("unit")
    if energy:
        if not is_nonnegative_finite(value) or not isinstance(unit, str):
            return None
        unit = unit.strip().casefold()
        if unit == "kcal":
            return value
        return value / 4.184 if unit == "kj" else None
    mass = resolve_product_quantity(value, unit)
    return mass[0] if mass is not None and mass[1] == "g" else None


def _normalize_label_set(label):
    if (
        not isinstance(label, dict)
        or label.get("source") not in _LABEL_SOURCES
        or label.get("preparation") != "as_sold"
    ):
        return None
    basis = _label_basis(label)
    nutrients = label.get("nutrients")
    if basis is None or not isinstance(nutrients, dict):
        return None
    calories = next((value for key in ("energy-kcal", "energy-kj", "energy")
                     if (value := _label_nutrient(nutrients, key, energy=True)) is not None), None)
    carbs = _label_nutrient(nutrients, "carbohydrates-total")
    carbohydrate_kind = None
    if carbs is not None:
        carbohydrate_kind = "total"
    elif _label_nutrient(nutrients, "carbohydrates") is not None:
        # OFF's available carbohydrate excludes fibre and cannot supply a total.
        carbohydrate_kind = "available"
    return {
        "label_source": label["source"],
        "basis": basis,
        "carbohydrate_kind": carbohydrate_kind,
        "macros": {
            "calories": calories,
            "protein_g": _label_nutrient(nutrients, "proteins"),
            "carbs_g": carbs,
            "fat_g": _label_nutrient(nutrients, "fat"),
        },
    }


def load_barcode_binding(code) -> dict:
    """Resolve a scanned barcode to a server-owned label snapshot, even if incomplete."""
    barcode = _normalized_barcode(code)
    if barcode is None:
        raise BarcodeNutritionLookupError("Invalid barcode")
    try:
        response = requests.get(
            f"{_OFF_ORIGIN}/api/v3.5/product/{barcode}",
            params={"fields": "code,product_name_th,product_name,generic_name,brands,nutrition"},
            headers={"User-Agent": "Homemade-Capstone/1.0 (student capstone project)"},
            timeout=10,
            allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise BarcodeNutritionLookupError("Could not verify product barcode") from exc

    if not isinstance(payload, dict) or payload.get("status") not in ("success", "success_with_warnings"):
        raise BarcodeNutritionLookupError("Product not found")
    product = payload.get("product")
    if not isinstance(product, dict) or _normalized_barcode(product.get("code")) != barcode:
        raise BarcodeNutritionLookupError("Product barcode did not match")
    name = next((value.strip() for key in ("product_name_th", "product_name", "generic_name", "brands")
                 if isinstance((value := product.get(key)), str) and value.strip()), None)
    if name is None:
        raise BarcodeNutritionLookupError("Product name was missing")
    nutrition = product.get("nutrition")
    input_sets = nutrition.get("input_sets") if isinstance(nutrition, dict) else None
    sets = []
    if isinstance(input_sets, list):
        sets = [label for item in input_sets if (label := _normalize_label_set(item)) is not None]
    return {"barcode": barcode, "product_name": name, "sets": sets}


def _scaled_macros(label, quantity):
    basis = label["basis"]["quantity"]
    values = {key: label["macros"][key] * (quantity / basis) for key in _MACRO_KEYS}
    return values if all(is_nonnegative_finite(value) for value in values.values()) else None


def _complete_label(label):
    if (
        not isinstance(label, dict)
        or label.get("label_source") not in _LABEL_SOURCES
        or label.get("carbohydrate_kind") != "total"
    ):
        return False
    basis, macros = label.get("basis"), label.get("macros")
    return (
        isinstance(basis, dict)
        and basis.get("unit") in ("g", "ml")
        and is_nonnegative_finite(basis.get("quantity"))
        and basis["quantity"] > 0
        and isinstance(macros, dict)
        and all(is_nonnegative_finite(macros.get(key)) for key in _MACRO_KEYS)
        and _scaled_macros(label, 100) is not None
    )


def _select_equivalent_label(labels):
    reference = _scaled_macros(labels[0], 100)
    for label in labels[1:]:
        values = _scaled_macros(label, 100)
        if any(not isclose(reference[key], values[key], rel_tol=1e-9, abs_tol=1e-9) for key in _MACRO_KEYS):
            return None
    return min(labels, key=lambda label: (label["label_source"], label["basis"]["quantity"]))


def _reviewed_conversion(barcode):
    try:
        records = json.loads(_PRODUCT_CONVERSIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(records, list):
        return None
    selected = None
    for record in records:
        if not isinstance(record, dict) or record.get("barcode") != barcode or record.get("preparation") != "as_sold":
            continue
        grams, milliliters, source = (record.get(key) for key in ("grams", "milliliters", "source_url"))
        if not isinstance(source, str) or not all(
            is_nonnegative_finite(amount) and amount > 0 for amount in (grams, milliliters)
        ):
            return None
        try:
            url = urlsplit(source)
            if url.scheme != "https" or not url.hostname:
                return None
        except ValueError:
            return None
        ratio = grams / milliliters
        if not is_nonnegative_finite(ratio) or ratio == 0:
            return None
        if selected is not None and not isclose(ratio, selected["grams"] / selected["milliliters"], rel_tol=1e-9):
            return None
        if selected is None:
            selected = {
                "barcode": barcode, "preparation": "as_sold", "grams": grams,
                "milliliters": milliliters, "source_url": source,
            }
    return selected


def product_display_nutrition(binding):
    """Populate the existing fridge display from one complete, unambiguous label."""
    complete = [label for label in binding["sets"] if _complete_label(label)]
    if len({label["basis"]["unit"] for label in complete}) != 1:
        return None
    selected = _select_equivalent_label(complete)
    return {"basis": "per_100g_or_ml", **_scaled_macros(selected, 100)} if selected is not None else None


def product_contribution(binding, quantity, unit):
    """Prefer compatible label data and report why the whole ingredient needs a fallback."""
    sets = binding.get("sets")
    if not isinstance(sets, list) or not sets:
        return None, "product_label_unavailable"
    complete = [label for label in sets if _complete_label(label)]
    if not complete:
        return None, "product_label_incomplete"
    resolved = resolve_product_quantity(quantity, unit)
    if resolved is None:
        return None, "product_quantity_unresolved"
    amount, basis_unit = resolved
    labels = [label for label in complete if label["basis"]["unit"] == basis_unit]
    conversion = None
    if not labels:
        conversion = _reviewed_conversion(binding.get("barcode"))
        if conversion is None:
            return None, "product_conversion_unavailable"
        if basis_unit == "g":
            amount = amount / conversion["grams"] * conversion["milliliters"]
            basis_unit = "ml"
        else:
            amount = amount / conversion["milliliters"] * conversion["grams"]
            basis_unit = "g"
        if not is_nonnegative_finite(amount):
            return None, "product_conversion_unavailable"
        labels = complete
    selected = _select_equivalent_label(labels)
    if selected is None:
        return None, "product_label_conflict"
    values = _scaled_macros(selected, amount)
    if values is None:
        return None, "product_quantity_unresolved"
    trace = {
        "source": "product_label",
        "label_source": selected["label_source"],
        "carbohydrate_kind": selected["carbohydrate_kind"],
        "basis": dict(selected["basis"]),
        "converted_quantity": {"amount": amount, "unit": basis_unit},
        "method": "direct_mass" if basis_unit == "g" else "direct_volume",
        "contribution": values,
    }
    if conversion is not None:
        trace["method"] = "reviewed_product_conversion"
        trace["conversion_evidence"] = conversion
    return trace, None
