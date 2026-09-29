# backend/eval/allergen_kg_eval.py
"""Allergen KG evaluation: (string, allergen) pair detection, floor-only vs floor ∪ KG,
plus a collision scan for KG-introduced false positives.

Usage (from backend/):
    venv/Scripts/python.exe -m eval.allergen_kg_eval
"""
import csv
import json

from allergen_kg.fixtures import make_memory_db
from allergen_kg.floor import ALLERGEN_MAP, FLOOR_BLOCKS
from allergen_kg.graph import get_allergen_closure
from allergen_kg.match import find_allergy_violation
from allergen_kg.resolve import resolve_blocks_for_keys
from database.seed_allergen_graph import seed_allergen_graph
from nutrition.text import normalize_thai

LABELS_PATH = "eval/fixtures/allergen_kg_labels.json"
INMU_PATH = "nutrition/data/inmu_nutrition_dataset.csv"


def _norm(s):
    return normalize_thai(s).lower()


def _resolver(seeded: bool):
    db = make_memory_db()
    if seeded:
        seed_allergen_graph(db)

    def resolve(keys):
        return resolve_blocks_for_keys(db, keys)
    return resolve


def empty_resolver():
    return _resolver(seeded=False)


def seeded_resolver():
    return _resolver(seeded=True)


def assert_graph_status(resolver, expected: str) -> None:
    """Abort unless every allergen key resolves with the expected graph_status.

    Guards against the silent-fallback failure class (MEMORY.md vLLM-LoRA entry):
    a "KG" arm that quietly fell back to the floor would compare the baseline to itself.
    """
    resolved = resolver(list(ALLERGEN_MAP))
    wrong = {key: r.graph_status for key, r in resolved.items() if r.graph_status != expected}
    if wrong:
        raise RuntimeError(f"expected graph_status={expected!r} for every key, got {wrong}")


def _is_literal(string, key):
    text = _norm(string)
    return any(_norm(t) in text for t in FLOOR_BLOCKS[key])


def _empty_by_key():
    return {
        key: {
            "literal": {"positives": 0, "caught": 0},
            "derived_only": {"positives": 0, "caught": 0, "caught_2plus_hop": 0},
            "negatives": {"total": 0, "flagged": 0},
        }
        for key in ALLERGEN_MAP
    }


def score_pairs(items, resolver, exclude_public: bool) -> dict:
    """Score every (string, allergen) pair.

    Top-level keys `literal` / `derived_only` / `negatives` are the headline strata.
    Extra breakdowns (so one seed edge or one allergen cannot pass for broad coverage):
      by_key                 -- the same strata per allergen key
      caught_by_head_edge    -- "<key>|<path joined ' -> '>" -> derived-only pairs caught via it
      spelling_note_items    -- note-bearing positive pairs: {"id", "caught"} (spelling-variant
                                misses are separable from compositional misses)
      floor_false_positives  -- labeled-negative pairs the checker flagged: {"id", "key"}
    """
    scores = {
        "literal": {"positives": 0, "caught": 0, "caught_2plus_hop": 0},
        "derived_only": {"positives": 0, "caught": 0, "caught_2plus_hop": 0},
        "negatives": {"total": 0, "flagged": 0},
        "by_key": _empty_by_key(),
        "caught_by_head_edge": {},
        "spelling_note_items": [],
        "floor_false_positives": [],
    }
    # One resolution per key (a closure query each), reused for every string.
    resolved_by_key = {key: resolver([key]) for key in ALLERGEN_MAP}
    for item in items:
        if exclude_public and item["public"]:
            continue
        for key in ALLERGEN_MAP:
            v = find_allergy_violation({"adjusted_ingredients": [item["string"]]}, {}, resolved_by_key[key])
            key_scores = scores["by_key"][key]
            if key in item["allergens"]:
                name = "literal" if _is_literal(item["string"], key) else "derived_only"
                stratum, key_stratum = scores[name], key_scores[name]
                stratum["positives"] += 1
                key_stratum["positives"] += 1
                two_plus = v is not None and bool(v.path) and len(v.path) >= 2
                if v is not None:
                    stratum["caught"] += 1
                    key_stratum["caught"] += 1
                    if two_plus:
                        stratum["caught_2plus_hop"] += 1
                        if name == "derived_only":
                            key_stratum["caught_2plus_hop"] += 1
                    if name == "derived_only":
                        edge = f"{key}|{' -> '.join(v.path) if v.path else 'floor'}"
                        scores["caught_by_head_edge"][edge] = scores["caught_by_head_edge"].get(edge, 0) + 1
                if item.get("note"):
                    scores["spelling_note_items"].append({"id": item["id"], "caught": v is not None})
            else:
                scores["negatives"]["total"] += 1
                key_scores["negatives"]["total"] += 1
                if v is not None:
                    scores["negatives"]["flagged"] += 1
                    key_scores["negatives"]["flagged"] += 1
                    scores["floor_false_positives"].append({"id": item["id"], "key": key})
    return scores


def collision_scan(inmu_names, pool_strings):
    db = make_memory_db()
    seed_allergen_graph(db)
    floor_terms = {t for terms in FLOOR_BLOCKS.values() for t in terms}
    hits = []
    for key in ALLERGEN_MAP:
        for entry in get_allergen_closure(db, key):
            if entry.name in floor_terms:
                continue
            node = _norm(entry.name)
            for source, strings in (("inmu", inmu_names), ("pool", pool_strings)):
                for s in strings:
                    if node in _norm(s):
                        hits.append({"node": entry.name, "allergen": key, "matched_string": s, "source": source})
    return hits


def main():
    labels = json.load(open(LABELS_PATH, encoding="utf-8"))
    items = labels["items"]
    floor_arm, kg_arm = empty_resolver(), seeded_resolver()
    assert_graph_status(floor_arm, "empty")
    assert_graph_status(kg_arm, "ok")
    report = {
        "key_definitions": labels["key_definitions"],
        "review_stats": labels["review_stats"],
    }
    for exclude_public in (False, True):
        tag = "without_public" if exclude_public else "all"
        report[tag] = {
            "n_strings": sum(1 for i in items if not (exclude_public and i["public"])),
            "floor_only": score_pairs(items, floor_arm, exclude_public),
            "floor_union_kg": score_pairs(items, kg_arm, exclude_public),
        }
    with open(INMU_PATH, encoding="utf-8") as f:
        inmu_names = [row["Thai_Name"] for row in csv.DictReader(f) if row.get("Thai_Name")]
    report["collision_hits"] = collision_scan(inmu_names, [i["string"] for i in items])
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    main()
