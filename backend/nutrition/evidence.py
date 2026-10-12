"""Pure qualification of trusted reviewed ingestion metadata, never source retrieval.

This checks binding/structure, not remote truth or reviewer authenticity. Real
accepted records require separately approved source verification and activation.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from types import MappingProxyType

from nutrition.text import normalize_alias
from nutrition.units import is_nonnegative_finite

_DEFINITIONS = {
    "calories": ("kcal", {"energy"}),
    "protein_g": ("g", {"protein"}),
    "carbs_g": ("g", {"total_carbohydrate", "carbohydrate_by_difference"}),
    "fat_g": ("g", {"total_fat"}),
}
_MARKERS = ("proxy", "energy_kcal", "carbs_g")


def has_reviewed_metadata(row):
    """Protect review history even when qualification fails or is incomplete."""
    derivation = row.derivation if row is not None else None
    return isinstance(derivation, dict) and any(
        key in derivation for key in ("nutrition_evidence", "g4_correction")
    )


@dataclass(frozen=True)
class EvidenceQualification:
    identity_verified: bool
    macros_verified: bool
    verified_portion_grams: Mapping[str, float]
    reasons: tuple[str, ...]


def _known(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {
        "unknown", "unresolved", "unspecified", "-",
    }


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _review_valid(review):
    if not isinstance(review, dict) or review.get("status") != "accepted":
        return False
    if not all(_known(review.get(k)) for k in ("reviewer", "receipt_ref")) or not _digest(review.get("receipt_sha256")):
        return False
    timestamp = review.get("reviewed_at_utc")
    if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
        return False
    try:
        return datetime.fromisoformat(timestamp[:-1] + "+00:00").utcoffset() == timezone.utc.utcoffset(None)
    except ValueError:
        return False


def _citation_valid(citation, source=None, source_ref=None):
    if not isinstance(citation, dict):
        return False
    if not all(_known(citation.get(k)) for k in (
        "publisher", "source", "source_ref", "release", "locator", "extraction",
    )) or not _digest(citation.get("artifact_sha256")):
        return False
    url = citation.get("url")
    if not isinstance(url, str) or re.fullmatch(r"https://[^\s/@?#]+(?:/[^\s]*)?", url) is None:
        return False
    return (source is None or citation["source"] == source) and (source_ref is None or citation["source_ref"] == source_ref)


def _entries(value, key):
    if not isinstance(value, list):
        return None
    indexed = {}
    for entry in value:
        if not isinstance(entry, dict) or not _known(entry.get(key)) or entry[key] in indexed:
            return None
        indexed[entry[key]] = entry
    return indexed


def _positive(value):
    return is_nonnegative_finite(value) and value > 0


def _binding_valid(binding, match, derivation):
    if not isinstance(binding, dict) or not all(_known(v) for v in (match.source, match.source_ref, match.ingredient_name)):
        return False
    macros = {key: getattr(match.macros, key) for key in _DEFINITIONS}
    portions = match.portion_grams or {}
    if match.portion_grams is not None and not isinstance(match.portion_grams, dict):
        return False
    bound_macros, bound_portions = binding.get("macros"), binding.get("portion_grams")
    if not isinstance(bound_macros, dict) or not isinstance(bound_portions, dict):
        return False
    for values in (macros, bound_macros):
        if set(values) != set(_DEFINITIONS) or any(v is not None and not is_nonnegative_finite(v) for v in values.values()):
            return False
    for values in (portions, bound_portions):
        if any(not _known(k) or not _positive(v) for k, v in values.items()):
            return False
    expected = {"source": match.source, "source_ref": match.source_ref,
                "ingredient_name": match.ingredient_name, "unit_basis": match.unit_basis,
                "macros": macros, "portion_grams": portions,
                "estimate_markers": {k: derivation[k] for k in _MARKERS if k in derivation}}
    return binding == expected and match.unit_basis in ("100g", "100ml")


def _portion_valid(entry, unit, factor, match, identity, review):
    if entry.get("review") != review or not _citation_valid(entry.get("citation")):
        return False
    if not all(_known(entry.get(k)) for k in ("portion_id", "description", "source_ingredient_name", "source_preparation", "source_unit")):
        return False
    target = {"source": match.source, "source_ref": match.source_ref,
              "ingredient_name": match.ingredient_name, "preparation": identity["preparation"]}
    equivalence, mapping = entry.get("equivalence"), entry.get("unit_mapping")
    if entry.get("target") != target or not isinstance(equivalence, dict) or not isinstance(mapping, dict):
        return False
    if equivalence.get("relation") != "exact" or not _known(equivalence.get("rationale")):
        return False
    if mapping.get("source_unit") != entry["source_unit"] or mapping.get("runtime_unit") != unit or not _known(mapping.get("rationale")):
        return False
    amount, weight, grams = (entry.get(k) for k in ("amount", "gram_weight", "grams_per_unit"))
    if not all(_positive(v) for v in (amount, weight, grams)) or entry.get("method") != "gram_weight/amount":
        return False
    computed = weight / amount
    return _positive(computed) and computed == grams == factor


def qualify_match(name, match) -> EvidenceQualification:
    """Missing/stale/contradictory evidence fails closed without changing numbers."""
    def result(identity=False, macros=False, portions=None, reasons=()):
        return EvidenceQualification(identity, macros, MappingProxyType(dict(portions or {})), tuple(reasons))

    derivation = match.derivation if isinstance(match.derivation, dict) else {}
    if "nutrition_evidence" not in derivation:
        return result()
    evidence = derivation["nutrition_evidence"]
    if not isinstance(evidence, dict) or type(evidence.get("schema_version")) is not int or evidence["schema_version"] != 1:
        return result(reasons=("unsupported or malformed nutrition evidence",))
    review = evidence.get("review")
    if not _review_valid(review) or not _binding_valid(evidence.get("row_binding"), match, derivation):
        return result(reasons=("nutrition evidence review/binding invalid or stale",))
    reasons = []
    identities = _entries(evidence.get("identity"), "alias")
    if identities is not None and any(alias != normalize_alias(alias) for alias in identities):
        identities = None
    identity = identities.get(normalize_alias(name)) if identities is not None and isinstance(name, str) else None
    identity_verified = bool(
        identity and identity.get("relation") == "exact" and "proxy" not in derivation
        and identity.get("ingredient_name") == match.ingredient_name
        and all(_known(identity.get(k)) for k in ("preparation", "rationale"))
        and identity.get("review") == review
        and _citation_valid(identity.get("citation"), match.source, match.source_ref)
    )
    if not identity_verified:
        reasons.append("nutrition evidence identity not verified for queried alias")

    macros = _entries(evidence.get("macros"), "key")
    macros_verified = macros is not None and set(macros) == set(_DEFINITIONS) and "proxy" not in derivation
    for key, (unit, definitions) in _DEFINITIONS.items():
        entry = macros.get(key, {}) if macros is not None else {}
        value = getattr(match.macros, key)
        marker = "energy_kcal" if key == "calories" else "carbs_g" if key == "carbs_g" else None
        valid = (
            is_nonnegative_finite(value) and is_nonnegative_finite(entry.get("value"))
            and entry["value"] == value and entry.get("unit") == unit
            and entry.get("basis") == match.unit_basis and isinstance(entry.get("definition"), str)
            and entry["definition"] in definitions
            and entry.get("origin") == "source_published" and marker not in derivation
            and _known(entry.get("source_field")) and entry.get("review") == review
            and _citation_valid(entry.get("citation"), match.source, match.source_ref)
            and ("publisher_method" not in entry or _known(entry["publisher_method"]))
        )
        macros_verified = macros_verified and valid
    if not macros_verified:
        reasons.append("nutrition evidence complete source-published macros not verified")

    portions, verified = _entries(evidence.get("portions"), "unit"), {}
    if portions is None:
        reasons.append("nutrition evidence portion entries malformed or conflicting")
    elif identity_verified:
        for unit, entry in portions.items():
            factor = (match.portion_grams or {}).get(unit)
            if _positive(factor) and _portion_valid(entry, unit, factor, match, identity, review):
                verified[unit] = factor
            else:
                reasons.append(f"nutrition evidence portion not verified: {unit}")
    return result(identity_verified, macros_verified, verified, reasons)
