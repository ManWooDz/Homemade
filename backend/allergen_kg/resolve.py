# backend/allergen_kg/resolve.py
"""Resolve the effective block set (floor ∪ KG closure) for flagged allergens.

Called once per request, before the retry loop. Never raises for a query
failure: the floor is always kept, and graph_status says what happened.
"""
import logging
from dataclasses import dataclass
from typing import Literal, Optional

from sqlalchemy.orm import Session

from allergen_kg.floor import FLOOR_BLOCKS, detect_flagged_allergens
from allergen_kg.graph import get_allergen_closure

log = logging.getLogger("allergen_kg")


@dataclass(frozen=True)
class TermInfo:
    matched_via: Literal["kg", "floor"]
    path: Optional[tuple[str, ...]]


@dataclass(frozen=True)
class ResolvedAllergen:
    terms: dict
    graph_status: Literal["ok", "empty", "unavailable"]


def floor_only(key: str, graph_status: str) -> ResolvedAllergen:
    return ResolvedAllergen(
        terms={term: TermInfo("floor", None) for term in FLOOR_BLOCKS[key]},
        graph_status=graph_status,
    )


def resolve_blocks_for_keys(db: Session, keys: list[str]) -> dict[str, ResolvedAllergen]:
    resolved = {}
    db_failed = False
    for key in keys:
        if db_failed:
            # First failure this request: don't pay another connection
            # timeout per remaining key -- floor only, immediately.
            resolved[key] = floor_only(key, "unavailable")
            continue
        try:
            closure = get_allergen_closure(db, key)
        except Exception:
            log.exception("[allergen_kg] closure query failed for '%s' -- using floor only", key)
            try:
                db.rollback()
            except Exception:
                log.warning("[allergen_kg] rollback after failed closure query for '%s' also failed", key, exc_info=True)
            db_failed = True
            resolved[key] = floor_only(key, "unavailable")
            continue

        if not closure:
            log.warning("[allergen_kg] graph has no terms for '%s' -- using floor only (seed missing?)", key)
            resolved[key] = floor_only(key, "empty")
            continue

        terms = {term: TermInfo("floor", None) for term in FLOOR_BLOCKS[key]}
        for entry in closure:
            terms[entry.name] = TermInfo("kg", entry.path)
        resolved[key] = ResolvedAllergen(terms=terms, graph_status="ok")
    return resolved


def resolve_allergy_blocks(db: Session, user_prefs) -> dict[str, ResolvedAllergen]:
    return resolve_blocks_for_keys(db, detect_flagged_allergens(user_prefs))


def unavailable_blocks(user_prefs) -> dict[str, ResolvedAllergen]:
    keys = detect_flagged_allergens(user_prefs)
    if keys:
        log.warning("[allergen_kg] graph unavailable -- floor only for %s", keys)
    return {key: floor_only(key, "unavailable") for key in keys}
