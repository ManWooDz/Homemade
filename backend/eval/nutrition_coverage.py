"""Headline evaluation: parse/match accuracy against an INDEPENDENTLY
hand-annotated ground-truth set (never lookup.py's own alias table --
circular, MEMORY.md's Circularity Trap entry). name_accuracy is over ALL
cases (parser correctness). row_correct/quantity_resolved/fully_grounded/
match_accuracy/coverage_rate are over the expected_in_db=True subset only
-- that's the denominator that answers "how well does grounding work,"
not diluted by cases annotated as correctly absent."""
from nutrition.lookup import match_ingredient
from nutrition.parser import parse_ingredient_string
from nutrition.units import resolve_grams

_QUANTITY_TOLERANCE_G = 0.01


def measure_match_accuracy(db, annotated_cases: list[dict]) -> dict:
    total = len(annotated_cases)
    name_correct = 0
    row_correct = 0
    quantity_resolved = 0
    fully_grounded = 0
    expected_in_db_count = 0

    for case in annotated_cases:
        parsed = parse_ingredient_string(case["raw"])
        if parsed.name == case["expected_name"]:
            name_correct += 1

        if not case["expected_in_db"]:
            continue
        expected_in_db_count += 1

        match = match_ingredient(db, parsed.name)
        if match is None or match.source_ref != case["expected_source_ref"]:
            continue
        row_correct += 1

        quantity_g = resolve_grams(parsed.quantity, parsed.unit, match.portion_grams)
        expected_g = case["expected_quantity_g"]
        quantity_matches = (
            quantity_g is not None and expected_g is not None
            and abs(quantity_g - expected_g) <= _QUANTITY_TOLERANCE_G
        )
        if quantity_matches:
            quantity_resolved += 1
            fully_grounded += 1

    return {
        "total": total,
        "name_correct": name_correct,
        "row_correct": row_correct,
        "quantity_resolved": quantity_resolved,
        "fully_grounded": fully_grounded,
        "expected_in_db_count": expected_in_db_count,
        "name_accuracy": name_correct / total if total else 0.0,
        "match_accuracy": row_correct / expected_in_db_count if expected_in_db_count else 0.0,
        "coverage_rate": fully_grounded / expected_in_db_count if expected_in_db_count else 0.0,
    }
