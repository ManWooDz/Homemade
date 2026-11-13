"""Exact mass factors and legacy water-density volume approximations.
Ingredient-specific portions take precedence; legacy entries lack evidence.
The numeric wrapper preserves usable estimates; detailed resolution keeps
them distinct from source-backed mass. Unknown/invalid units stay unresolved."""
from dataclasses import dataclass
from collections.abc import Mapping
from math import isfinite

_MASS_UNIT_GRAMS: dict[str, float] = {
    "กรัม": 1.0, "ก.": 1.0, "กิโลกรัม": 1000.0, "กก.": 1000.0,
    "ขีด": 100.0, "มิลลิกรัม": 0.001, "มก.": 0.001,
}

_VOLUME_UNIT_MILLILITERS: dict[str, float] = {
    "มล.": 1.0, "มิลลิลิตร": 1.0, "ลิตร": 1000.0,
    "cl": 10.0, "dl": 100.0,
    "ถ้วยตวง": 240.0,
    "ช้อนโต๊ะ": 15.0,
    "ช้อนชา": 5.0,
}

GLOBAL_UNIT_GRAMS = {**_MASS_UNIT_GRAMS, **_VOLUME_UNIT_MILLILITERS}
_PRODUCT_MASS_UNITS = {
    **_MASS_UNIT_GRAMS, "g": 1.0, "kg": 1000.0, "mg": 0.001, "μg": 0.000001, "mcg": 0.000001,
}
_PRODUCT_VOLUME_UNITS = {**_VOLUME_UNIT_MILLILITERS, "ml": 1.0, "l": 1000.0}


@dataclass(frozen=True)
class GramResolution:
    grams: float | None
    method: str
    source_backed: bool | None


def is_nonnegative_finite(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return isfinite(value) and value >= 0
    except OverflowError:
        return False


def resolve_product_quantity(quantity: float | None, unit: str | None) -> tuple[float, str] | None:
    """Normalize mass or volume without changing the type of measurement."""
    if not is_nonnegative_finite(quantity) or not isinstance(unit, str):
        return None
    unit = unit.strip().casefold()
    for factors, basis_unit in ((_PRODUCT_MASS_UNITS, "g"), (_PRODUCT_VOLUME_UNITS, "ml")):
        if unit in factors:
            amount = quantity * factors[unit]
            return (amount, basis_unit) if is_nonnegative_finite(amount) else None
    return None


def resolve_grams_detailed(quantity: float | None, unit: str | None, portion_grams: dict | None,
                           *, verified_portion_grams: Mapping[str, float] | None = None) -> GramResolution:
    unresolved = GramResolution(None, "unresolved", None)
    if not is_nonnegative_finite(quantity) or not isinstance(unit, str) or not unit:
        return unresolved
    if portion_grams is not None and not isinstance(portion_grams, dict):
        return unresolved
    if portion_grams and unit in portion_grams:
        factor = portion_grams[unit]
        method, source_backed = "ingredient_portion", None
        if isinstance(verified_portion_grams, Mapping):
            verified_factor = verified_portion_grams.get(unit)
            if is_nonnegative_finite(verified_factor) and verified_factor > 0 and verified_factor == factor:
                source_backed = True
    elif unit in GLOBAL_UNIT_GRAMS:
        factor = GLOBAL_UNIT_GRAMS[unit]
        source_backed = unit in _MASS_UNIT_GRAMS
        method = "direct_mass" if source_backed else "water_density_approximation"
    else:
        return unresolved
    if not is_nonnegative_finite(factor) or factor == 0:
        return unresolved
    grams = quantity * factor
    if not is_nonnegative_finite(grams):
        return unresolved
    return GramResolution(grams, method, source_backed)


def resolve_grams(quantity: float | None, unit: str | None, portion_grams: dict | None) -> float | None:
    return resolve_grams_detailed(quantity, unit, portion_grams).grams
