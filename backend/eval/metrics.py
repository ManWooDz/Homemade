import re
import unicodedata

from main import validate_recipe

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

# Mirrors the pantry-staple allowlist in generators/prompts.py's prompt
# text (main.py's call_agentic_llm() prompt, rule 6) — kept in sync
# manually since it's a fixed, rarely-changing list.
_PANTRY_STAPLES = ["เกลือ", "พริกไทย", "น้ำมัน", "น้ำปลา", "ซีอิ๊ว", "น้ำตาล", "น้ำเปล่า"]


def check_schema_and_constraints(recipe: dict, ingredients_name_only: list, user_prefs: dict) -> dict:
    """Thin wrapper around the existing validate_recipe() 6-stage pipeline
    (imported read-only from main.py — main.py is not modified by this
    plan). Named distinctly from the design doc's Evaluation 2 (hidden/
    indirect allergen detection, not built this milestone) so a report
    never conflates the two: this covers explicit/known-allergen and
    schema/constraint failures only."""
    result = validate_recipe(recipe, ingredients_name_only, user_prefs)
    if result["status"] == "pass":
        return {"valid": True, "reason": None}
    return {"valid": False, "reason": result["reason"]}


def check_ingredient_hallucination(recipe: dict, ingredients: list) -> dict:
    """Flags adjusted_ingredients entries that don't reference any of the
    user's actual ingredients or an allowed pantry staple. Substring match
    (not exact), since adjusted_ingredients entries include quantities,
    e.g. 'หมูสับ 200 กรัม' for the ingredient 'หมูสับ'.

    Known limitation: because matching is substring-based, a short known
    ingredient/staple name that is itself a substring of a longer, different
    ingredient's name produces a false negative — e.g. 'ไก่' (chicken meat)
    is a substring of 'ไข่ไก่' (chicken egg), so a hallucinated 'ไข่ไก่' will
    NOT be flagged when the user only has 'ไก่'. Do not over-trust this
    metric for such near-miss cases."""
    allowed = list(ingredients) + _PANTRY_STAPLES
    unknown = []
    for item in recipe.get("adjusted_ingredients", []) if isinstance(recipe, dict) else []:
        normalized_item = _normalize_thai(item)
        if not any(_normalize_thai(known) in normalized_item for known in allowed):
            unknown.append(item)
    return {"hallucinated": len(unknown) > 0, "unknown_ingredients": unknown}


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
    total_latency = sum(r.get("latency_seconds", 0.0) for r in results)

    return {
        "n": n,
        "schema_validity_rate": valid_count / n,
        "hallucination_rate": hallucinated_count / n,
        "mean_latency_seconds": total_latency / n,
    }
