import re

_LEADING_BULLET = re.compile(r"^[-•]\s*")
_NAME_PREFIX = re.compile(r"^([^\d(]+)")


def extract_ingredient_name(raw: str) -> str:
    """Best-effort extraction of the ingredient name from a raw recipe
    line like 'กุ้งนาง 4 ตัว' -> 'กุ้งนาง'. Heuristic: everything before
    the first digit or parenthesis. Falls back to the whole (stripped)
    string when no digit/paren is present (e.g. 'พริกไทยป่นพอควร').
    Known limitation, same class as check_ingredient_hallucination's own
    documented substring-matching limitations: does not handle every
    real-world phrasing, only what's needed for keyword/position-based
    Tier A non-essential-ingredient detection (design spec §4.1)."""
    s = _LEADING_BULLET.sub("", raw).strip()
    match = _NAME_PREFIX.match(s)
    return match.group(1).strip() if match else s


def dish_families_overlap(name_a: str, name_b: str, keyword_pairs: list[tuple[str, str]]) -> bool:
    """True if name_a and name_b share a dish family -- used to build the
    eval-fixture exclusion list (design spec §3.1). The source dataset's
    dish names are Thai; eval fixture base_recipe names are English/
    transliterated (e.g. "Som Tam") -- a single-language substring check
    can never match across scripts, so keyword_pairs holds (thai_form,
    english_form) tuples and this checks both name-orderings."""
    for thai_kw, english_kw in keyword_pairs:
        if (thai_kw in name_a and english_kw in name_b) or (thai_kw in name_b and english_kw in name_a):
            return True
    return False
