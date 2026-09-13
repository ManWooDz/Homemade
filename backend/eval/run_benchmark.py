# backend/eval/run_benchmark.py
"""Manual benchmark entry point — not run by the automated test suite.

Requires a real GEMINI_API_KEY (for the Gemini baseline) and/or a running
vLLM server reachable at LOCAL_LLM_BASE_URL (for the Qwen candidates) to
produce real numbers; with neither configured, every generator call
returns an {"error": ...} dict and every case is scored as invalid, which
is expected and not a bug in this script.

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
    start = time.monotonic()
    recipe = generator.generate(ingredients_name_only, case["user_prefs"], case["base_recipe"])
    latency = time.monotonic() - start

    if isinstance(recipe, dict) and "error" in recipe:
        return {"case_id": case["case_id"], "valid": False, "hallucinated": True, "latency_seconds": latency, "reason": recipe["error"]}

    schema_result = check_schema_and_constraints(recipe, ingredients_name_only, case["user_prefs"])
    hallucination_result = check_ingredient_hallucination(recipe, ingredients_name_only)

    return {
        "case_id": case["case_id"],
        "valid": schema_result["valid"],
        "reason": schema_result["reason"],
        "hallucinated": hallucination_result["hallucinated"],
        "unknown_ingredients": hallucination_result["unknown_ingredients"],
        "latency_seconds": latency,
    }


def run_benchmark():
    cases = load_cases()
    candidates = {
        "gemini_baseline": GeminiGenerator(),
        "qwen_4b": LocalLLMGenerator(model="qwen2.5-4b-instruct"),
        "qwen_7b_9b": LocalLLMGenerator(model="qwen2.5-7b-instruct"),
    }

    report = {}
    for name, generator in candidates.items():
        per_case = [run_case(generator, case) for case in cases]
        report[name] = {"per_case": per_case, "summary": summarize_run(per_case)}

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    run_benchmark()
