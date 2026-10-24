import re
import unicodedata

from main import validate_recipe
from recipe_checks import unknown_ingredients
from recipe_instructions import instruction_uses

_THAI_TONE_MARKS = "่้๊๋"  # mai ek/tho/tri/chattawa


def _normalize_thai(s: str) -> str:
    """Canonicalizes Thai text for substring comparison. Plain
    unicodedata.normalize("NFC", ...) does NOT unify these forms -- Thai
    SARA AM (ำ, U+0E33) has no canonical decomposition mapping in the
    Unicode Character Database, so NFC never merges it with the
    visually-identical NIKHAHIT+SARA AA sequence some text sources emit.
    Verified directly (2026-09-21) before trusting this; see MEMORY.md."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("ำ", "ํา")  # SARA AM -> NIKHAHIT + SARA AA
    s = re.sub(f"ํ([{_THAI_TONE_MARKS}])", r"\1ํ", s)  # tone mark before nikhahit
    return s

# Legacy compatibility constant; admission uses recipe_checks identities.
_PANTRY_STAPLES = ["เกลือ", "พริกไทย", "น้ำมัน", "น้ำปลา", "ซีอิ๊ว", "น้ำตาล", "น้ำเปล่า"]


def check_schema_and_constraints(recipe: dict, ingredients_name_only: list, user_prefs: dict,
                                 resolved_blocks=None) -> dict:
    """Thin wrapper around the existing validate_recipe() 6-stage pipeline
    (imported from main.py). Named distinctly from the design doc's Evaluation 2 (hidden/
    indirect allergen detection, not built this milestone) so a report
    never conflates the two: this covers explicit/known-allergen and
    schema/constraint failures only.

    Pass resolved_blocks to use the allergen KG path; generator-benchmark
    numbers produced this way are a new baseline (2026-09) and are not
    comparable to earlier spec.md rows."""
    result = validate_recipe(recipe, ingredients_name_only, user_prefs, resolved_blocks=resolved_blocks)
    if result["status"] == "pass":
        return {"valid": True, "reason": None}
    return {"valid": False, "reason": result["reason"]}


def check_ingredient_hallucination(recipe: dict, ingredients: list) -> dict:
    """Declaration-only metric; says nothing about free-text instruction completeness."""
    unknown = unknown_ingredients(recipe, ingredients)
    return {"hallucinated": bool(unknown), "unknown_ingredients": unknown}


def check_instruction_consistency(recipe):
    if not isinstance(recipe, dict) or "_instruction_plan" not in recipe:
        return "unknown"  # Legacy prose cannot establish complete ingredient coverage.
    try:
        instruction_uses(recipe)
        return "valid"
    except (ValueError, TypeError, KeyError):
        return "invalid"


def summarize_run(results: list) -> dict:
    """Aggregates a list of per-case result dicts (each with "valid",
    "hallucinated", "latency_seconds") into rates the design doc's
    Evaluation 1 asks for."""
    n = len(results)
    if n == 0:
        return {
            "n": 0,
            "schema_validity_rate": 0.0,
            "hallucination_rate": 0.0,
            "mean_latency_seconds": 0.0,
        }

    valid_count = sum(1 for r in results if r.get("valid"))
    hallucinated_count = sum(1 for r in results if r.get("hallucinated"))
    evaluated_count = sum(isinstance(r.get("hallucinated"), bool) for r in results)
    total_latency = sum(r.get("latency_seconds", 0.0) for r in results)

    return {
        "n": n,
        "schema_validity_rate": valid_count / n,
        "hallucination_rate": hallucinated_count / evaluated_count if evaluated_count else None,
        "hallucination_evaluated_n": evaluated_count,
        "generator_error_count": sum(r.get("generation_status") == "provider_error" for r in results),
        "format_error_count": sum(r.get("generation_status") == "format_error" for r in results),
        "instruction_consistency_counts": {status: sum(r.get("instruction_consistency") == status for r in results)
                                           for status in ("valid", "invalid", "unknown", "not_evaluated")},
        "mean_latency_seconds": total_latency / n,
    }
