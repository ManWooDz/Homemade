# backend/allergen_kg/match.py
"""Pure, ingredient-scoped allergen matching over already-resolved blocks."""
import re
from dataclasses import dataclass
from typing import Literal, Optional

from allergen_kg.floor import (
    ALLERGEN_LABELS, ALLERGEN_MAP, DERIVED_FLOOR_TERMS, LITERAL_KG_TERMS,
    detect_flagged_allergens, term_spans,
)
from allergen_kg.resolve import ResolvedAllergen, floor_only
from nutrition.text import normalize_thai


@dataclass(frozen=True)
class Violation:
    term: str
    allergen_key: str
    matched_via: str
    path: Optional[tuple[str, ...]]
    match_kind: Literal["literal", "derived"] = "literal"
    uncertain: bool = False


def _norm(s: str) -> str:
    return normalize_thai(s).lower()


def _ordered_terms(resolved: ResolvedAllergen):
    def sort_key(item):
        term, info = item
        return (-(len(info.path) if info.path else 0), -len(term), term)
    return sorted(resolved.terms.items(), key=sort_key)


# ponytail: explicit claims in delimited notes only; unsupported/conditional
# language stays blocked. Add reviewed phrases, not a general negation guess.
_ABSENCE_PREFIX = re.compile(r"ไม่มีส่วนผสมของ\s*|ปราศจาก\s*|ไม่มี\s*|without\s+|free\s+from\s+|no\s+")
_CLAIM_CONTEXT = re.compile(r"(?:^|[\(\[,;:])\s*(?:สูตร\s*)?$")
_AMBIGUOUS_CLAIM = re.compile(r"\b(?:if|may|might|unless)\b|อาจ|ถ้า|หาก|ตรวจสอบ|ไม่แน่ใจ|\?")


def _absence_spans(text, key, terms):
    if _AMBIGUOUS_CLAIM.search(text):
        return []
    targets = {_norm(t) for t in (*terms, *ALLERGEN_MAP[key]["triggers"])}
    if key == "milk":
        targets.update(("นมวัว", "นมผง", "cow milk"))
    target_pattern = "(?:" + "|".join(re.escape(t) for t in sorted(targets, key=len, reverse=True)) + ")"
    spans = []
    for prefix in _ABSENCE_PREFIX.finditer(text):
        if not _CLAIM_CONTEXT.search(text[:prefix.start()]):
            continue
        target = re.match(target_pattern, text[prefix.end():])
        if target is None:
            continue
        end = prefix.end() + target.end()
        tail = text[end:]
        # A claim must end at the note boundary, not introduce trailing prose.
        if tail and not re.match(r"\s*(?:$|[)\]])", tail):
            continue
        spans.append((prefix.end(), end))
    for suffix in re.finditer(target_pattern + r"[- ]free\b", text):
        if (_CLAIM_CONTEXT.search(text[:suffix.start()])
                and re.match(r"\s*(?:$|[)\]])", text[suffix.end():])):
            spans.append(suffix.span())
    return spans


def find_allergy_violation(recipe: dict, user_prefs, resolved_blocks: dict) -> Optional[Violation]:
    keys = list(detect_flagged_allergens(user_prefs))
    keys += [key for key in resolved_blocks if key not in keys]
    lines = [(_norm(line), line.lower()) for line in recipe["adjusted_ingredients"]]

    for key in keys:
        resolved = resolved_blocks.get(key) or floor_only(key, "unavailable")
        scoped_lines = [(text, raw, _absence_spans(text, key, resolved.terms)) for text, raw in lines]
        for term, info in _ordered_terms(resolved):
            normalized_term = _norm(term)
            for text, raw_text, absent in scoped_lines:
                hits = [span for span in term_spans(text, normalized_term, key)
                        if not any(a <= span[0] and span[1] <= b for a, b in absent)]
                # Preserve a conservative catch for malformed Latin text whose
                # combining mark would hide the allergen after NFC normalization.
                malformed = bool(normalized_term.isascii() and re.search(
                    re.escape(normalized_term) + r"(?=[\u0300-\u036f])", raw_text))
                if hits or malformed:
                    literal_names = (*ALLERGEN_MAP[key]["triggers"], *LITERAL_KG_TERMS.get(key, ()))
                    derived = term in DERIVED_FLOOR_TERMS.get(key, ()) or (
                        info.path is not None and term not in literal_names)
                    uncertain = malformed or normalized_term in ("แป้ง", "flour")
                    return Violation(term, key, info.matched_via, info.path,
                                     "derived" if derived else "literal", uncertain)
    return None


def format_violation_reason(v: Violation) -> str:
    if v.uncertain:
        return (f"Allergy violation: ยังยืนยันส่วนประกอบของ '{v.term}' ไม่ได้ "
                f"(ผู้ใช้แพ้ {v.allergen_key})")
    if v.path and len(v.path) >= 2:
        chain = " → ".join([f"'{v.path[0]}'", *v.path[1:], ALLERGEN_LABELS[v.allergen_key]])
        return f"Allergy violation: {chain} (ผู้ใช้แพ้ {v.allergen_key})"
    if v.match_kind == "derived":
        return (f"Allergy violation: พบ '{v.term}' ที่มีส่วนประกอบของ "
                f"{ALLERGEN_LABELS[v.allergen_key]} (ผู้ใช้แพ้ {v.allergen_key})")
    return f"Allergy violation: พบ '{v.term}' ในสูตร (ผู้ใช้แพ้ {v.allergen_key})"


def head_contains_other_terms(head: str, other_terms: list[str]) -> list[str]:
    """Historical structural substring check used only to audit chain redundancy."""
    normalized_head = _norm(head)
    return [t for t in other_terms if t != head and _norm(t) in normalized_head]
