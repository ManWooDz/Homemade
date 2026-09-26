"""GLOBAL_UNIT_GRAMS: ingredient-independent conversions (exact SI
multiples, plus มล./ลิตร treated 1:1 with grams as a documented
water-density approximation). The Thai measuring units ถ้วยตวง (1 US cup
= 240 mL), ช้อนโต๊ะ (1 tbsp = 15 mL) and ช้อนชา (1 tsp = 5 mL) are exact
volume definitions (values from a standard home-cooking unit-conversion
reference supplied by the user -- widely published, not a USDA/INMU
citation) and use the SAME 1 mL ~ 1 g water-density approximation: it
over-counts less-dense ingredients (oil ~0.92 g/mL, granulated sugar
~0.85 g/mL) and is only a fallback -- an ingredient's own portion_grams
entry for the same unit (e.g. น้ำตาล's curated "ช้อนโต๊ะ") is checked
first and wins. Any other unit depends on the specific
ingredient and is only resolved via that ingredient's own portion_grams
-- checked first, so a curated override always wins. No default is ever
guessed for an unresolvable unit."""

GLOBAL_UNIT_GRAMS: dict[str, float] = {
    "กรัม": 1.0, "ก.": 1.0, "กิโลกรัม": 1000.0, "กก.": 1000.0,
    "ขีด": 100.0, "มิลลิกรัม": 0.001, "มก.": 0.001,
    "มล.": 1.0, "มิลลิลิตร": 1.0, "ลิตร": 1000.0,
    "ถ้วยตวง": 240.0,  # 1 US cup = 240 mL, water-density approximation (same policy as มล./ลิตร above)
    "ช้อนโต๊ะ": 15.0,  # 1 tablespoon = 15 mL, water-density approximation
    "ช้อนชา": 5.0,  # 1 teaspoon = 5 mL, water-density approximation
}


def resolve_grams(quantity: float | None, unit: str | None, portion_grams: dict | None) -> float | None:
    if quantity is None or unit is None:
        return None
    if portion_grams and unit in portion_grams:
        return quantity * portion_grams[unit]
    if unit in GLOBAL_UNIT_GRAMS:
        return quantity * GLOBAL_UNIT_GRAMS[unit]
    return None
