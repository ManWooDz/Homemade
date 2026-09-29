# backend/eval/build_allergen_label_pool.py
"""Builds the pre-registered ingredient-string pool for the allergen KG eval.

Usage (from backend/):
    venv/Scripts/python.exe -m eval.build_allergen_label_pool OUT_JSON INMU_N [BENCHMARK_SAMPLE] -- BENCHMARK_JSON...
"""
import csv
import hashlib
import json
import random
import re
import sys

from allergen_kg.floor import ALLERGEN_MAP
from nutrition.text import normalize_thai

PUBLIC_TEXT_PATHS = ["../spec.md", "../MEMORY.md", "../AGENTS.md"]
_REVIEW_COLUMNS = ["id", "string", "source", "file", "allergens", "public"]

POOL_RULE = (
    "Benchmark strings: every adjusted_ingredients string from the listed benchmark JSON files, cleaned with "
    "clean_string() (normalize_thai(strip()) with zero-width characters U+200B/U+200C/U+200D/U+FEFF removed) and "
    "deduplicated; strings matched by is_garbled() are excluded; if BENCHMARK_SAMPLE is set, a random.Random(42) "
    "sample of that many of the sorted surviving strings. Then every MOCK_RECIPES ingredient string in "
    "database/seed_postgres.py that is not already in the pool. Then INMU rows with a non-empty Thai_Name from "
    "nutrition/data/inmu_nutrition_dataset.csv, sampled with random.Random(42) from the CSV rows in file order "
    "(INMU_N rows), deduplicated against everything already in the pool, so INMU may yield fewer than INMU_N "
    "items. Source attribution priority is benchmark > base_recipe > inmu. Stored strings are in normalize_thai "
    "form."
)

# Character sets are built from code points (chr) so the source file holds no invisible/combining characters.
_THAI = f"{chr(0x0E00)}-{chr(0x0E7F)}"
_THAI_COMBINING = f"{chr(0x0E31)}{chr(0x0E34)}-{chr(0x0E3A)}{chr(0x0E47)}-{chr(0x0E4E)}"
# 1/2, 1/4, 3/4, ~, en dash, em dash, *, ;, curly double quotes, curly single quotes, ellipsis
_EXTRA_ALLOWED = "".join(chr(c) for c in (0xBD, 0xBC, 0xBE, 0x7E, 0x2013, 0x2014, 0x2A, 0x3B,
                                          0x201C, 0x201D, 0x2018, 0x2019, 0x2026))
_ZERO_WIDTH = "".join(chr(c) for c in (0x200B, 0x200C, 0x200D, 0xFEFF))
_ALLOWED_CHARS = re.compile(rf"^[{_THAI}A-Za-z0-9\s.,()\-/%:+&'\"{re.escape(_EXTRA_ALLOWED)}]*$")
_MARK_AFTER_NON_THAI = re.compile(rf"[^{_THAI}][{_THAI_COMBINING}]")
_THAI_LETTER = re.compile(f"[{chr(0x0E01)}-{chr(0x0E2E)}]")
_LOWER_LATIN_LETTER = re.compile(r"[a-z]")
_REASONING_LEAK = re.compile(r"[A-Za-z]{3,}:")


def clean_string(s: str) -> str:
    """normalize_thai(s.strip()) with zero-width characters removed."""
    for ch in _ZERO_WIDTH:
        s = s.replace(ch, "")
    return normalize_thai(s.strip())


def is_garbled(s: str):
    if not _ALLOWED_CHARS.match(s):
        return "character outside Thai/Latin/digits/basic punctuation"
    if _MARK_AFTER_NON_THAI.search(s):
        return "Thai combining mark attached to a non-Thai character"
    if _REASONING_LEAK.search(s):
        return "reasoning-leak shape"
    for token in re.split(r"[\s()/]+", s):
        if _THAI_LETTER.search(token) and _LOWER_LATIN_LETTER.search(token):
            return f"token mixes Thai and lowercase Latin letters: {token!r}"
    return None


def ingredient_name(s: str) -> str:
    return normalize_thai(re.split(r"[0-9(]", s, maxsplit=1)[0].strip()).lower()


def load_public_text(paths=PUBLIC_TEXT_PATHS) -> str:
    texts = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            texts.append(normalize_thai(f.read()).lower())
    return "\n".join(texts)


def is_public(s: str, public_text: str) -> bool:
    """Public if the whole ingredient name, or its first whitespace-separated token, occurs in public_text."""
    name = ingredient_name(s)
    if not name:
        return False
    first_token = name.split()[0]
    return any(len(c) >= 2 and c in public_text for c in (name, first_token))


def canonical_sha256(obj) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def export_review_tsv(pool: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(_REVIEW_COLUMNS)
        for item in pool["items"]:
            writer.writerow([item["id"], item["string"], item["source"], item["file"],
                             ",".join(item["allergens"] or []), "yes" if item["public"] else "no"])


def import_review_tsv(pool: dict, path: str) -> dict:
    """Takes ONLY the allergens column back; aborts if any row's string no longer matches the pool."""
    by_id = {item["id"]: item for item in pool["items"]}
    reviewed = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if reader.fieldnames != _REVIEW_COLUMNS:
            raise ValueError(f"unexpected header {reader.fieldnames}; expected tab-delimited {_REVIEW_COLUMNS}")
        for row in reader:
            item_id = int(row["id"])
            if item_id in reviewed:
                raise ValueError(f"duplicate row id={item_id}")
            if item_id not in by_id or row["string"] != by_id[item_id]["string"]:
                raise ValueError(f"row id={row['id']} string changed or unknown -- file was re-encoded or edited")
            keys = [k.strip() for k in (row["allergens"] or "").split(",") if k.strip()]
            unknown = [k for k in keys if k not in ALLERGEN_MAP]
            if unknown:
                raise ValueError(f"row id={item_id}: unknown allergen keys {unknown}")
            reviewed[item_id] = sorted(set(keys))
    if set(reviewed) != set(by_id):
        raise ValueError(f"missing rows: {sorted(set(by_id) - set(reviewed))}")
    out = json.loads(json.dumps(pool, ensure_ascii=False))
    for item in out["items"]:
        item["allergens"] = reviewed[item["id"]]
    return out


def _load_benchmark(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    start = 0 if raw.startswith("{") else raw.find("\n{") + 1
    return json.loads(raw[start:])


def build_pool(benchmark_paths, inmu_csv_path, inmu_n, benchmark_sample, public_text, mock_recipes=None) -> dict:
    """mock_recipes: optional list of {"name", "ingredients"} dicts; default is database.seed_postgres.MOCK_RECIPES."""
    seen_benchmark = set()
    excluded = []
    benchmark_items = []
    for path in sorted(benchmark_paths):
        report = _load_benchmark(path)
        for candidate in report.values():
            for case in candidate.get("per_case", []):
                recipe = case.get("recipe")
                if not isinstance(recipe, dict):
                    continue
                for s in recipe.get("adjusted_ingredients") or []:
                    if not isinstance(s, str):
                        continue
                    norm = clean_string(s)
                    if not norm or norm in seen_benchmark:
                        continue
                    seen_benchmark.add(norm)
                    reason = is_garbled(norm)
                    file_name = path.replace("\\", "/").split("/")[-1]
                    if reason:
                        excluded.append({"string": norm, "reason": reason, "source": file_name})
                    else:
                        benchmark_items.append({"string": norm, "source": "benchmark", "file": file_name})

    if benchmark_sample is not None:
        benchmark_items.sort(key=lambda i: i["string"])
        benchmark_items = random.Random(42).sample(benchmark_items, benchmark_sample)

    # Only strings actually in the pool (or excluded as garbled) block later sources; unsampled benchmark
    # strings must not swallow a base-recipe string.
    seen = {i["string"] for i in benchmark_items} | {e["string"] for e in excluded}

    if mock_recipes is None:
        from database.seed_postgres import MOCK_RECIPES as mock_recipes
    base_items = []
    for r in mock_recipes:
        for s in r["ingredients"]:
            norm = clean_string(s)
            if norm and norm not in seen:
                seen.add(norm)
                base_items.append({"string": norm, "source": "base_recipe", "file": f"seed_postgres.py:{r['name']}"})

    with open(inmu_csv_path, encoding="utf-8") as f:
        rows = [row for row in csv.DictReader(f) if row.get("Thai_Name")]
    inmu_items = []
    for row in random.Random(42).sample(rows, inmu_n):
        norm = clean_string(row["Thai_Name"])
        if norm and norm not in seen:
            seen.add(norm)
            inmu_items.append({"string": norm, "source": "inmu", "file": f"INMU:{row['Food_Code']}"})

    items = benchmark_items + base_items + inmu_items
    for index, item in enumerate(items):
        item["id"] = index
        item["allergens"] = None
        item["public"] = is_public(item["string"], public_text)

    return {
        "pool_rule": POOL_RULE,
        "edge_semantics": "A → B means a typical preparation of A contains B",
        "inmu_n": inmu_n,
        "benchmark_sample": benchmark_sample,
        "random_seed": 42,
        "excluded": excluded,
        "items": items,
    }


if __name__ == "__main__":
    sep = sys.argv.index("--")
    head, paths = sys.argv[1:sep], sys.argv[sep + 1:]
    out_path, inmu_n = head[0], int(head[1])
    sample = int(head[2]) if len(head) > 2 else None
    pool = build_pool(paths, "nutrition/data/inmu_nutrition_dataset.csv", inmu_n, sample, load_public_text())
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)
    by_source = {s: sum(i["source"] == s for i in pool["items"]) for s in ("benchmark", "base_recipe", "inmu")}
    print(f"items={len(pool['items'])} (benchmark={by_source['benchmark']} base_recipe={by_source['base_recipe']} "
          f"inmu={by_source['inmu']}) excluded={len(pool['excluded'])} "
          f"judgments={len(pool['items']) * len(ALLERGEN_MAP)} public={sum(i['public'] for i in pool['items'])}")
