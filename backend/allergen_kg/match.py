# backend/allergen_kg/match.py
"""Pure allergen matching over already-resolved blocks. No DB access."""
from dataclasses import dataclass
from typing import Optional

from allergen_kg.floor import ALLERGEN_LABELS, detect_flagged_allergens
from allergen_kg.resolve import ResolvedAllergen, floor_only
from nutrition.text import normalize_thai


@dataclass(frozen=True)
class Violation:
    term: str
    allergen_key: str
    matched_via: str
    path: Optional[tuple[str, ...]]


def _norm(s: str) -> str:
    return normalize_thai(s).lower()


def _ordered_terms(resolved: ResolvedAllergen):
    def sort_key(item):
        term, info = item
        return (-(len(info.path) if info.path else 0), -len(term), term)
    return sorted(resolved.terms.items(), key=sort_key)


def find_allergy_violation(recipe: dict, user_prefs, resolved_blocks: dict) -> Optional[Violation]:
    text = _norm(" ".join(recipe["adjusted_ingredients"]))
    keys = list(detect_flagged_allergens(user_prefs))
    keys += [key for key in resolved_blocks if key not in keys]

    for key in keys:
        resolved = resolved_blocks.get(key) or floor_only(key, "unavailable")
        for term, info in _ordered_terms(resolved):
            if _norm(term) in text:
                return Violation(term=term, allergen_key=key, matched_via=info.matched_via, path=info.path)
    return None


def format_violation_reason(v: Violation) -> str:
    if v.matched_via == "kg" and v.path:
        chain = " → ".join([f"'{v.path[0]}'", *v.path[1:], ALLERGEN_LABELS[v.allergen_key]])
        return f"Allergy violation: {chain} (ผู้ใช้แพ้ {v.allergen_key})"
    return f"Allergy violation: พบ '{v.term}' ในสูตร (ผู้ใช้แพ้ {v.allergen_key})"


def head_contains_other_terms(head: str, other_terms: list[str]) -> list[str]:
    """Terms (other than head) that already sit inside head after normalization.

    Non-empty means a chain ending at `head` is redundant: a shorter node
    already catches any string containing head.
    """
    normalized_head = _norm(head)
    return [t for t in other_terms if t != head and _norm(t) in normalized_head]
