# backend/eval/run_benchmark.py
"""Manual benchmark entry point — not run by the automated test suite.

Behavior depends entirely on the credentials/services actually configured
in the environment this is run from — this script does NOT sandbox or
mock either candidate:

- If a real GEMINI_API_KEY is configured (e.g. in backend/.env), running
  this script makes a REAL, BILLED API call to Gemini for the
  gemini_baseline candidate. That is intentional for a real benchmark run,
  but it means running this is not automatically "safe" — do not run it
  casually in an environment where GEMINI_API_KEY is a live key.
- If a vLLM server is reachable at LOCAL_LLM_BASE_URL, the Qwen candidates
  produce real numbers against it.
- Only for whichever of the two is NOT configured does that generator's
  calls return an {"error": ...} dict (every case for it then scores as
  invalid) — this is a per-candidate fallback, not a blanket "safe no-op"
  guarantee for the whole script.

Usage (from backend/, with .env configured):
    python -m eval.run_benchmark
"""
import json
import time

from eval.metrics import check_ingredient_hallucination, check_schema_and_constraints, summarize_run
from generators.gemini_generator import GeminiGenerator
from generators.local_generator import LocalLLMGenerator

FIXTURES_PATH = "eval/fixtures/generator_eval_cases.json"


def load_cases():
    with open(FIXTURES_PATH, encoding="utf-8") as f:
        return json.load(f)


def run_case(generator, case):
    ingredients_name_only = [i["name"] for i in case["ingredients"]]
    input_snapshot = {
        "ingredients": ingredients_name_only,
        "user_prefs": case["user_prefs"],
        "base_recipe": case["base_recipe"],
    }
    start = time.monotonic()
    recipe = generator.generate(ingredients_name_only, case["user_prefs"], case["base_recipe"])
    latency = time.monotonic() - start

    if isinstance(recipe, dict) and "error" in recipe:
        return {"case_id": case["case_id"], "valid": False, "hallucinated": True, "latency_seconds": latency, "reason": recipe["error"], "recipe": recipe, "input": input_snapshot}

    schema_result = check_schema_and_constraints(recipe, ingredients_name_only, case["user_prefs"])
    hallucination_result = check_ingredient_hallucination(recipe, ingredients_name_only)

    return {
        "case_id": case["case_id"],
        "valid": schema_result["valid"],
        "reason": schema_result["reason"],
        "hallucinated": hallucination_result["hallucinated"],
        "unknown_ingredients": hallucination_result["unknown_ingredients"],
        "latency_seconds": latency,
        "recipe": recipe,
        "input": input_snapshot,
    }


def run_benchmark():
    cases = load_cases()
    # NOTE — prompt asymmetry: GeminiGenerator always calls build_recipe_prompt()
    # with include_example=False, while LocalLLMGenerator (both Qwen candidates)
    # always uses include_example=True (see generators/local_generator.py) —
    # a deliberate few-shot boost aimed at smaller local models, not a bug.
    # This means gemini_baseline vs. either qwen_* row below varies BOTH model
    # and prompt at once, so it is not a clean model-only comparison. Only
    # qwen_4b vs. qwen_7b_9b is prompt-matched (both include_example=True).
    candidates = {
        "gemini_baseline": GeminiGenerator(),
        # Verified real model IDs (2026-09-18) — Qwen2.5 has no 4B or 9B size;
        # Qwen3.5 does, and Qwen3.5-9B is documented as fitting a single 24GB
        # GPU, matching this project's chosen benchmark GPU tier.
        "qwen_4b": LocalLLMGenerator(model="qwen3.5-4b"),
        "qwen_7b_9b": LocalLLMGenerator(model="qwen3.5-9b"),
    }

    report = {}
    for name, generator in candidates.items():
        per_case = [run_case(generator, case) for case in cases]
        report[name] = {"per_case": per_case, "summary": summarize_run(per_case)}

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    run_benchmark()
