# backend/eval/retry_convergence.py
"""Retry-exhaustion rate, floor-only vs floor ∪ KG, through the real retry loop.

Makes REAL, BILLED Gemini calls when run as a script. main() refuses to run
unless CONFIRM_GEMINI_CALLS equals the exact planned maximum call count
(k x cases x 2 arms x 3 attempts), so the run only happens after the budget was
confirmed. The generator is imported lazily, only after that guard passes.

Usage (from backend/):
    CONFIRM_GEMINI_CALLS=<max_calls> venv/Scripts/python.exe -m eval.retry_convergence K CASE_ID [CASE_ID ...]
"""
import json
import os
import sys

from allergen_kg.floor import detect_flagged_allergens
from eval.allergen_kg_eval import assert_graph_status, empty_resolver, seeded_resolver

FIXTURES_PATH = "eval/fixtures/generator_eval_cases.json"
ARMS = 2
MAX_ATTEMPTS = 3


def run_arm(cases, resolve, generate_fn, k):
    from main import run_generation_with_validation
    rows = []
    for case in cases:
        names = [i["name"] for i in case["ingredients"]]
        keys = detect_flagged_allergens(case["user_prefs"])
        resolved = resolve(keys)
        resolved_status = resolved[keys[0]].graph_status if keys else "none"
        for run in range(1, k + 1):
            final, log = run_generation_with_validation(
                generate_fn, names, [n.lower() for n in names], case["user_prefs"], case["base_recipe"], resolved)
            rows.append({
                "case_id": case["case_id"], "run": run,
                "exhausted": final is None, "attempts": len(log),
                "reasons": [e["reason"] for e in log if e["reason"]],
                "resolved_status": resolved_status,
                "final_valid": final is not None and not (isinstance(final, dict) and "error" in final),
            })
    return rows


def summarize(rows):
    out = {}
    for r in rows:
        s = out.setdefault(r["case_id"], {"runs": 0, "exhausted": 0})
        s["runs"] += 1
        s["exhausted"] += int(r["exhausted"])
    return out


def overall(rows):
    return {"runs": len(rows), "exhausted": sum(int(r["exhausted"]) for r in rows)}


def check_confirmation(k, n_cases, env_value):
    """Return the planned maximum Gemini call count, or SystemExit unless env_value == that number."""
    max_calls = k * n_cases * ARMS * MAX_ATTEMPTS
    if env_value != str(max_calls):
        raise SystemExit(
            f"refusing to make billed Gemini calls: planned maximum is {max_calls} "
            f"(k={k} x {n_cases} cases x {ARMS} arms x {MAX_ATTEMPTS} attempts). "
            f"Set CONFIRM_GEMINI_CALLS={max_calls} to confirm (got {env_value!r})."
        )
    return max_calls


def _load_generator():
    from main import call_agentic_llm
    return call_agentic_llm


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2:
        raise SystemExit("usage: python -m eval.retry_convergence K CASE_ID [CASE_ID ...]")
    try:
        k = int(argv[0])
    except ValueError:
        raise SystemExit(f"K must be a positive integer, got {argv[0]!r}")
    if k < 1:
        raise SystemExit(f"K must be a positive integer, got {k}")
    wanted = set(argv[1:])
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        cases = [c for c in json.load(f) if c["case_id"] in wanted]
    missing = wanted - {c["case_id"] for c in cases}
    if missing:
        raise SystemExit(f"unknown case ids: {sorted(missing)}")
    floor_arm, kg_arm = empty_resolver(), seeded_resolver()
    assert_graph_status(floor_arm, "empty")
    assert_graph_status(kg_arm, "ok")

    planned = k * len(cases) * ARMS * MAX_ATTEMPTS
    print(f"planned maximum Gemini calls: {planned} "
          f"(k={k} x {len(cases)} cases x {ARMS} arms x {MAX_ATTEMPTS} attempts)", file=sys.stderr)
    check_confirmation(k, len(cases), os.environ.get("CONFIRM_GEMINI_CALLS"))

    generate_fn = _load_generator()
    report = {}
    for arm, resolve in (("floor_only", floor_arm), ("floor_union_kg", kg_arm)):
        rows = run_arm(cases, resolve, generate_fn, k)
        report[arm] = {"overall": overall(rows), "summary": summarize(rows), "rows": rows}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    main()
