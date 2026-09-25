"""GLOBAL_UNIT_GRAMS: ingredient-independent conversions (exact SI
multiples, plus มล./ลิตร treated 1:1 with grams as a documented
water-density approximation). Any other unit depends on the specific
ingredient and is only resolved via that ingredient's own portion_grams
-- checked first, so a curated override always wins. No default is ever
guessed for an unresolvable unit."""

GLOBAL_UNIT_GRAMS: dict[str, float] = {
    "กรัม": 1.0, "ก.": 1.0, "กิโลกรัม": 1000.0, "กก.": 1000.0,
    "ขีด": 100.0, "มิลลิกรัม": 0.001, "มก.": 0.001,
    "มล.": 1.0, "มิลลิลิตร": 1.0, "ลิตร": 1000.0,
}


def resolve_grams(quantity: float | None, unit: str | None, portion_grams: dict | None) -> float | None:
    if quantity is None or unit is None:
        return None
    if portion_grams and unit in portion_grams:
        return quantity * portion_grams[unit]
    if unit in GLOBAL_UNIT_GRAMS:
        return quantity * GLOBAL_UNIT_GRAMS[unit]
    return None
