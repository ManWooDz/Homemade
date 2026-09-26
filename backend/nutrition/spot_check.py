"""Verification tooling for Task 14 (INMU spot-check) -- NOT part of the
runtime nutrition pipeline (nothing in main.py imports this). Throwaway
script kept for reproducibility, not a permanent production module.

Captures two things from the 2026-09-26 spot-check (see spec.md's
"Current state" entry of the same date for the actual findings):

1. `get_candidates()` -- the candidate-selection query: seeds a throwaway
   in-memory SQLite DB with the real CSV via `seed_inmu.import_csv()` (same
   approach Task 9 used -- no live Postgres needed, `IngredientNutrition`
   uses plain `sqlalchemy.JSON`, SQLite-compatible), then filters for rows
   whose `derivation["carbs_g"]` is `"by_difference"` or
   `"by_difference_clamped"` and samples a fixed-seed pick of each.

2. `check_against_inmu()` -- the live-site lookup used for the actual
   2026-09-26 spot-check. INMU's site (inmu.mahidol.ac.th/thaifcd) has no
   documented per-food search API; this reverse-engineers the same AJAX
   calls the site's own JS makes (`appassistant/get_json_food_name`
   autocomplete, then `foodsearch/food_name_result`), found by reading
   `foodsearch/food_name`'s inline `<script>` block. This is NOT the
   `foodsearch/by_nutrient` page named in the original task brief -- that
   page is a nutrient-range search across many foods, not a per-food
   lookup, and has no obvious way to query a single named ingredient.
   IMPORTANT, confirmed empirically: querying INMU's site with a Thai-text
   `term=` (either UTF-8 or TIS-620/cp874 percent-encoded) does not filter
   correctly server-side -- it reliably returns a near-unfiltered ~5,279-row
   response instead of real matches. English-text `term=` values filter
   correctly. So this function queries by each row's `English_Name` and
   cross-checks the response's own "Food Code" field against the expected
   `source_ref` to confirm it landed on the same row -- it does NOT
   validate Thai-name search on INMU's site, only the underlying macro
   values for a row confirmed by food code.

Usage:
    python nutrition/spot_check.py                  # candidate selection only (no network)
    python nutrition/spot_check.py --check-inmu      # prints a reminder of what's needed to
                                                      # re-run the live INMU comparison -- it does
                                                      # NOT run it automatically (see note below)

Known limitation: the 15 English_Name values used for the actual
2026-09-26 live-INMU comparison are not stored anywhere in this repo (only
`get_candidates()`'s query/sampling logic is committed) -- `English_Name`
isn't a column on `IngredientNutrition`, only present in the source CSV
row that `seed_inmu.import_csv()` reads once and doesn't persist. A future
re-run of `check_against_inmu()` needs to re-derive each candidate's
English_Name from the CSV by `source_ref`/`Food_Code` first (`--check-inmu`
does not do this for you); this script is not fully self-contained/one-
command-reproducible for the live-comparison half.
"""
import argparse
import json
import random
import re
import sys
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, IngredientNutrition, IngredientNutritionAlias
from nutrition.seed_inmu import import_csv

_DEFAULT_CSV_PATH = "nutrition/data/inmu_nutrition_dataset.csv"
_INMU_BASE = "https://inmu.mahidol.ac.th/thaifcd"
_INMU_HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_candidates(csv_path: str = _DEFAULT_CSV_PATH, seed: int = 42,
                    n_clamped: int = 3, n_by_difference: int = 12) -> dict:
    """Builds a throwaway in-memory SQLite DB from the real CSV and returns
    a fixed-seed sample of by_difference / by_difference_clamped rows.

    Returns {"by_difference": [...], "by_difference_clamped": [...],
    "counts": {"by_difference": N, "by_difference_clamped": N}} where each
    row is a dict of the fields needed for a spot-check comparison.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[
        IngredientNutrition.__table__, IngredientNutritionAlias.__table__,
    ])
    db = Session(engine)
    import_csv(db, csv_path)

    rows = db.query(IngredientNutrition).all()
    by_diff = [r for r in rows if r.derivation and r.derivation.get("carbs_g") == "by_difference"]
    clamped = [r for r in rows if r.derivation and r.derivation.get("carbs_g") == "by_difference_clamped"]

    rng = random.Random(seed)
    clamped_pick = rng.sample(clamped, min(n_clamped, len(clamped)))
    byd_pick = rng.sample(by_diff, min(n_by_difference, len(by_diff)))

    def _row_dict(r):
        return {
            "id": r.id, "ingredient_name": r.ingredient_name, "source_ref": r.source_ref,
            "calories": r.calories, "protein_g": r.protein_g, "fat_g": r.fat_g,
            "carbs_g": r.carbs_g, "derivation": r.derivation,
        }

    return {
        "by_difference": [_row_dict(r) for r in byd_pick],
        "by_difference_clamped": [_row_dict(r) for r in clamped_pick],
        "counts": {"by_difference": len(by_diff), "by_difference_clamped": len(clamped)},
    }


def _inmu_autocomplete(session, term: str) -> list:
    r = session.get(
        f"{_INMU_BASE}/appassistant/get_json_food_name",
        params={"food_group_id": "", "term": term},
        headers=_INMU_HEADERS, timeout=20,
    )
    r.encoding = "utf-8"
    return json.loads(r.text.lstrip("﻿"))


def _inmu_fetch_detail(session, food_id: str, dbcode: str, name: str) -> str:
    r = session.get(
        f"{_INMU_BASE}/foodsearch/food_name_result",
        params={
            "order_fields": "", "order_directions": "", "page_no": "1", "status": "A",
            "selected_name": name, "selected_id": food_id, "selected_dbcode": dbcode,
            "food_group_id": "", "food_name": name, "mode": "food_group_result",
        },
        headers=_INMU_HEADERS, timeout=20,
    )
    r.encoding = "utf-8"
    return r.text


def _extract_food_code(html: str) -> str | None:
    m = re.search(r'Food Code:\s*</div>\s*<div[^>]*>([^<]+)</div>', html)
    return m.group(1).strip() if m else None


def _extract_field(html: str, label: str) -> str | None:
    rows = re.findall(
        r'<td class="">([^<]+)</td>\s*<td class="">[^<]*</td>\s*<td class="text-center">([^<]*)</td>',
        html,
    )
    for lbl, val in rows:
        if lbl.strip() == label:
            return val.strip()
    return None


def check_against_inmu(candidate_row: dict, english_name: str, session=None) -> dict:
    """Looks up one candidate row (from get_candidates()) against INMU's
    live site by English name, returns a dict comparing our stored values
    to INMU's live "Energy, by calculation" / "Protein, total" /
    "Fat, total" / "Carbohydrate, available" fields. Requires network
    access. `session` may be a pre-built requests.Session (reused across
    calls to avoid re-establishing a session cookie each time); one is
    created if omitted.
    """
    import requests

    if session is None:
        session = requests.Session()
        session.get(f"{_INMU_BASE}/foodsearch/food_name", headers=_INMU_HEADERS, timeout=20)

    matches = _inmu_autocomplete(session, english_name)
    exact = [m for m in matches if m["name"].strip().lower() == english_name.strip().lower()]
    if not exact:
        return {"source_ref": candidate_row["source_ref"], "error": f"no autocomplete match for {english_name!r} ({len(matches)} results)"}

    chosen = None
    for m in exact:
        html = _inmu_fetch_detail(session, m["id"], m["dbcode"], m["name"])
        fc = _extract_food_code(html)
        if fc == candidate_row["source_ref"]:
            chosen = (m, html, fc)
            break
    if chosen is None:
        m = exact[0]
        html = _inmu_fetch_detail(session, m["id"], m["dbcode"], m["name"])
        chosen = (m, html, _extract_food_code(html))

    m, html, fc = chosen
    return {
        "source_ref": candidate_row["source_ref"],
        "food_code_match": fc == candidate_row["source_ref"],
        "inmu_food_code": fc,
        "ours": {
            "calories": candidate_row["calories"], "protein_g": candidate_row["protein_g"],
            "fat_g": candidate_row["fat_g"], "carbs_g": candidate_row["carbs_g"],
        },
        "inmu": {
            "calories": _extract_field(html, "Energy, by calculation"),
            "protein_g": _extract_field(html, "Protein, total"),
            "fat_g": _extract_field(html, "Fat, total"),
            "carbs_available_g": _extract_field(html, "Carbohydrate, available"),
            "carbs_total_g": _extract_field(html, "Carbohydrate, total"),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=_DEFAULT_CSV_PATH)
    parser.add_argument("--check-inmu", action="store_true",
                         help="does NOT auto-run the live comparison -- prints what's still needed "
                              "to do so (English_Name isn't persisted/committed anywhere); see module "
                              "docstring's 'Known limitation' note")
    args = parser.parse_args()

    candidates = get_candidates(args.csv)
    print(f"by_difference candidates: {len(candidates['by_difference'])} "
          f"(of {candidates['counts']['by_difference']} total)")
    print(f"by_difference_clamped candidates: {len(candidates['by_difference_clamped'])} "
          f"(of {candidates['counts']['by_difference_clamped']} total)")
    for tag in ("by_difference_clamped", "by_difference"):
        for row in candidates[tag]:
            print(f"  [{tag}] {row['source_ref']} | {row['ingredient_name']} | "
                  f"kcal={row['calories']} protein={row['protein_g']} "
                  f"fat={row['fat_g']} carbs={row['carbs_g']}")

    if args.check_inmu:
        print("\n--check-inmu requires each row's English_Name (not stored on "
              "IngredientNutrition -- re-derive from the CSV, see the "
              "2026-09-26 spot-check for the exact 15 names used). This flag "
              "is a hook for a future re-run, not a fully automatic one.")


if __name__ == "__main__":
    sys.exit(main())
