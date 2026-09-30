# backend/eval/retry_convergence.py
"""Retry-exhaustion rate, floor-only vs floor ∪ KG, through the real retry loop.

Makes REAL, BILLED Gemini calls when run as a script. main() refuses to run
unless CONFIRM_GEMINI_CALLS equals the exact planned maximum call count
(k x cases x 2 arms x 3 attempts), so the run only happens after the budget was
confirmed. The generator is imported lazily, only after that guard passes.

Usage (from backend/):
    CONFIRM_GEMINI_CALLS=<max_calls> venv/Scripts/python.exe -m eval.retry_convergence [--out PATH] K CASE_ID [CASE_ID ...]

Progress output from the generation loop goes to stderr; only the JSON report
goes to stdout (or to --out PATH). After arm 1, <PATH>.partial.json is written.
Exit status 3 if any generation call returned an error dict (report still written).
"""
import argparse
import contextlib
import json
import os
import sys

from allergen_kg.floor import detect_flagged_allergens
from eval.allergen_kg_eval import assert_graph_status, empty_resolver, seeded_resolver

FIXTURES_PATH = "eval/fixtures/generator_eval_cases.json"
ARMS = 2
MAX_ATTEMPTS = 3


def run_arm(cases, resolve, generate_fn, k):
    from main import build_llm_prefs, run_generation_with_validation
    rows = []
    for case in cases:
        names = [i["name"] for i in case["ingredients"]]
        keys = detect_flagged_allergens(case["user_prefs"])
        resolved = resolve(keys)
        statuses = {key: resolved[key].graph_status for key in keys}
        resolved_status = statuses[keys[0]] if keys else "none"
        for run in range(1, k + 1):
            final, log = run_generation_with_validation(
                generate_fn, names, [n.lower() for n in names], case["user_prefs"], case["base_recipe"], resolved,
                # same prompt the endpoint sends: user prefs + this arm's forbidden terms
                llm_prefs=build_llm_prefs(case["user_prefs"], resolved))
            errored = isinstance(final, dict) and "error" in final
            rows.append({
                "case_id": case["case_id"], "run": run,
                "exhausted": final is None, "attempts": len(log),
                "reasons": [e["reason"] for e in log if e["reason"]],
                "resolved_status": resolved_status,
                "resolved_statuses": statuses,
                "final_valid": final is not None and not errored,
                "errored": errored,
                "error_details": (final.get("details") or final["error"]) if errored else None,
            })
    return rows


def _counts(rows):
    return {
        "runs": len(rows),
        "exhausted": sum(int(r["exhausted"]) for r in rows),
        "errored": sum(int(r["errored"]) for r in rows),
        "passed": sum(int(r["final_valid"]) for r in rows),
    }


def summarize(rows):
    by_case = {}
    for r in rows:
        by_case.setdefault(r["case_id"], []).append(r)
    return {case_id: _counts(case_rows) for case_id, case_rows in by_case.items()}


def overall(rows):
    return _counts(rows)


def check_confirmation(k, n_cases, env_value):
    """Return the planned maximum Gemini call count, or SystemExit unless env_value == that number."""
    if k < 1 or n_cases < 1:
        raise SystemExit(f"k and number of cases must both be >= 1 (got k={k}, cases={n_cases})")
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


def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="python -m eval.retry_convergence")
    parser.add_argument("k", type=int)
    parser.add_argument("case_ids", nargs="+", metavar="CASE_ID")
    parser.add_argument("--out", default=None, help="write the JSON report here instead of stdout")
    args = parser.parse_args(argv)
    k = args.k
    if k < 1:
        raise SystemExit(f"K must be a positive integer, got {k}")
    wanted = set(args.case_ids)
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
    # the generation loop prints progress to stdout; keep stdout clean for the JSON report
    with contextlib.redirect_stdout(sys.stderr):
        for arm, resolve in (("floor_only", floor_arm), ("floor_union_kg", kg_arm)):
            rows = run_arm(cases, resolve, generate_fn, k)
            report[arm] = {"overall": overall(rows), "summary": summarize(rows), "rows": rows}
            if args.out:
                _write_json(args.out + ".partial.json", report)
            print(f"arm {arm} finished: {report[arm]['overall']}", file=sys.stderr)

    if args.out:
        _write_json(args.out, report)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    errored = [r for arm in report.values() for r in arm["rows"] if r["errored"]]
    if errored:
        ids = sorted({r["case_id"] for r in errored})
        print(
            "!" * 70 + "\n"
            f"WARNING: {len(errored)} run(s) returned a generator ERROR dict (not counted as exhausted).\n"
            f"Cases affected: {ids}\n"
            f"First error_details: {errored[0]['error_details']}\n"
            "The exhaustion counts in this report are NOT trustworthy for those cases.\n"
            + "!" * 70,
            file=sys.stderr,
        )
        raise SystemExit(3)
    return report


if __name__ == "__main__":
    main()
