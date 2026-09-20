"""Assembles the QLoRA SFT dataset from thai_food_v1.0, enforcing the
Tier B >= 50% floor (design spec §4.4) and excluding eval-fixture
near-duplicates (design spec §3.1).

Usage (from backend/, with pandas/openpyxl installed):
    python -m finetune.build_dataset \
        --xlsx "C:\\Users\\Hp\\Desktop\\Homemade\\pythainlpthai_food_v1.0\\thai_food_parsed.xlsx" \
        --fixtures eval/fixtures/generator_eval_cases.json \
        --out finetune_dataset.jsonl
"""
import argparse
import json
import random

from .examples import build_tier_a_examples, build_tier_b_examples
from .exclusion import find_excluded_recipes
from .recipe_source import load_recipes


def assemble(xlsx_path: str, fixtures_path: str, seed: int = 0) -> list[dict]:
    with open(fixtures_path, encoding="utf-8") as f:
        fixtures = json.load(f)
    fixture_names = [c["base_recipe"]["name"] for c in fixtures]

    recipes = load_recipes(xlsx_path)
    excluded = {r.dish_name for r in find_excluded_recipes(recipes, fixture_names)}
    pool = [r for r in recipes if r.dish_name not in excluded]

    tier_a, tier_b = [], []
    for recipe in pool:
        tier_a.extend(build_tier_a_examples(recipe))
        tier_b.extend(build_tier_b_examples(recipe))

    rng = random.Random(seed)
    rng.shuffle(tier_a)
    rng.shuffle(tier_b)

    # Enforce Tier B >= 50% floor (design spec §4.4) by capping Tier A,
    # never by fabricating extra Tier B examples.
    max_tier_a = len(tier_b)
    if len(tier_a) > max_tier_a:
        tier_a = tier_a[:max_tier_a]

    combined = tier_a + tier_b
    rng.shuffle(combined)
    return combined


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx", required=True)
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    examples = assemble(args.xlsx, args.fixtures, seed=args.seed)
    tier_a_count = sum(1 for e in examples if e["tier"] == "A")
    tier_b_count = sum(1 for e in examples if e["tier"] == "B")

    with open(args.out, "w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")

    print(f"wrote {len(examples)} examples to {args.out}")
    print(f"tier A: {tier_a_count} ({tier_a_count/len(examples):.1%})")
    print(f"tier B: {tier_b_count} ({tier_b_count/len(examples):.1%})")


if __name__ == "__main__":
    main()
