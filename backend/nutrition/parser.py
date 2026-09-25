"""Thai ingredient-string parser. A numeric range ("1-2") or a vague word
("เล็กน้อย") is `unparsed`, never guessed a default."""
import re
from dataclasses import dataclass
from typing import Literal

_VAGUE_QUANTITY_WORDS = ["เล็กน้อย", "ตามชอบ", "พอประมาณ", "ตามต้องการ"]

# (Step 5, real Gemini output, 2026-09-25) A parenthetical clarifying note
# can appear anywhere in the string -- not only trailing at the very end
# (e.g. "กะปิเจ (ทำจากถั่วเหลืองหรือธัญพืช) 1 ช้อนโต๊ะ", where the note sits
# before the quantity/unit). Stripped globally, not anchored to `$`, so a
# mid-string note doesn't get folded into the name by the name group's
# backtracking.
_PARENTHETICAL_NOTE_RE = re.compile(r"\s*\([^)]*\)\s*")
_RANGE_RE = re.compile(r"\d+\s*-\s*\d+")
_QUANTITY_UNIT_RE = re.compile(
    r"^(?P<name>.+?)\s*(?P<quantity>\d+/\d+|\d+(?:[.,]\d+)?)\s*(?P<unit>[ก-๙\.]+)\s*$"
)


@dataclass
class ParsedIngredient:
    raw: str
    name: str
    quantity: float | None
    unit: str | None
    parse_status: Literal["ok", "unparsed"]


def _parse_quantity_token(token: str) -> float | None:
    if "/" in token:
        num, _, den = token.partition("/")
        try:
            denominator = float(den)
            return float(num) / denominator if denominator else None
        except ValueError:
            return None
    try:
        return float(token.replace(",", "."))
    except ValueError:
        return None


def parse_ingredient_string(raw: str) -> ParsedIngredient:
    text = raw.strip()
    core_text = _PARENTHETICAL_NOTE_RE.sub(" ", text).strip()

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

    name = match.group("name").strip(" ,()")
    if not name:
        return ParsedIngredient(raw=raw, name=core_text, quantity=None, unit=None, parse_status="unparsed")

    quantity = _parse_quantity_token(match.group("quantity"))
    if quantity is None:
        return ParsedIngredient(raw=raw, name=core_text, quantity=None, unit=None, parse_status="unparsed")

    return ParsedIngredient(raw=raw, name=name, quantity=quantity, unit=match.group("unit").strip(), parse_status="ok")
