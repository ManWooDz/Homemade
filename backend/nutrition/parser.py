"""Parse explicit quantities only; ambiguous amounts/identity notes abstain."""
import re
from dataclasses import dataclass
from math import isfinite
from typing import Literal

_VAGUE_QUANTITY_WORDS = ["เล็กน้อย", "ตามชอบ", "พอประมาณ", "ตามต้องการ"]

_RANGE_RE = re.compile(r"\d+\s*-\s*\d+")
_NUMERIC_COMMA_RE = re.compile(r"\d\s*,\s*\d")
_BAD_AMOUNT_PREFIX_RE = re.compile(r"(?:[+\-−–/]\s*|\d[.,]\s*|(?:^|\s)\d+(?:\.\d+)?[eE][+\-]?\s*)$")
_MASS_SUFFIXES = {"g": "กรัม", "kg": "กิโลกรัม", "mg": "มิลลิกรัม"}
_QUANTITY_UNIT_RE = re.compile(
    r"^(?P<name>.+?)\s+(?P<quantity>\d+/\d+|\d+(?:\.\d+)?)\s*(?P<unit>kg|mg|g|[ก-๙\.]+)\s*$"
)


@dataclass
class ParsedIngredient:
    raw: str
    name: str
    quantity: float | None
    unit: str | None
    parse_status: Literal["ok", "unparsed"]


def _parse_quantity_token(token: str) -> float | None:
    try:
        if "/" in token:
            num, _, den = token.partition("/")
            numerator = float(num)
            denominator = float(den)
            if not isfinite(numerator) or not isfinite(denominator) or denominator <= 0:
                return None
            quantity = numerator / denominator
        else:
            quantity = float(token)
        return quantity if isfinite(quantity) and quantity >= 0 else None
    except (ValueError, OverflowError):
        return None


def parse_ingredient_string(raw: str) -> ParsedIngredient:
    text = raw.strip()
    # shortcut: notes may change ingredient identity; parse them only after a reviewed note contract.
    if "(" in text or ")" in text or _NUMERIC_COMMA_RE.search(text):
        return ParsedIngredient(raw, text, None, None, "unparsed")
    core_text = text

    for vague_word in _VAGUE_QUANTITY_WORDS:
        if vague_word in core_text:
            name = core_text.replace(vague_word, "").strip(" ,()")
            return ParsedIngredient(raw=raw, name=name or core_text, quantity=None, unit=None, parse_status="unparsed")

    if _RANGE_RE.search(core_text):
        match = re.match(r"^(?P<name>.+?)\s*\d+\s*-\s*\d+", core_text)
        name = match.group("name").strip(" ,()") if match else core_text
        return ParsedIngredient(raw=raw, name=name or core_text, quantity=None, unit=None, parse_status="unparsed")

    match = _QUANTITY_UNIT_RE.match(core_text)
    if not match:
        return ParsedIngredient(raw=raw, name=core_text, quantity=None, unit=None, parse_status="unparsed")

    name = match.group("name").strip()
    token = match.group("quantity")
    if not name or _BAD_AMOUNT_PREFIX_RE.search(name) or ("/" in token and re.search(r"(?:^|\s)\d+$", name)):
        return ParsedIngredient(raw=raw, name=core_text, quantity=None, unit=None, parse_status="unparsed")

    quantity = _parse_quantity_token(token)
    if quantity is None:
        return ParsedIngredient(raw=raw, name=core_text, quantity=None, unit=None, parse_status="unparsed")

    unit = match.group("unit")
    return ParsedIngredient(raw=raw, name=name, quantity=quantity, unit=_MASS_SUFFIXES.get(unit, unit), parse_status="ok")
