# backend/eval/allergen_kg_eval.py
"""Allergen KG evaluation: (string, allergen) pair detection, floor-only vs floor ∪ KG,
plus a collision scan for KG-introduced false positives.

Usage (from backend/):
    venv/Scripts/python.exe -m eval.allergen_kg_eval
"""
import argparse
import csv
import json
import hashlib
from pathlib import Path

from allergen_kg.fixtures import make_memory_db
from allergen_kg.floor import ALLERGEN_MAP, FLOOR_BLOCKS
from allergen_kg.graph import get_allergen_closure
from allergen_kg.match import find_allergy_violation
from allergen_kg.resolve import resolve_blocks_for_keys
from database.seed_allergen_graph import seed_allergen_graph
from eval.build_allergen_label_pool import canonical_sha256
from nutrition.text import normalize_thai

LABELS_PATH = "eval/fixtures/allergen_kg_labels.json"
HISTORICAL_KEYS = ("shrimp", "peanut", "milk", "egg", "gluten", "shellfish", "fish", "soy", "nut")
V2_KEYS = (*HISTORICAL_KEYS, "sesame")
# Frozen v1 stratification, not the current runtime floor or composition policy.
HISTORICAL_FLOOR_BLOCKS = {
    "shrimp": ("shrimp", "prawn", "กุ้ง", "กะปิ"),
    "peanut": ("peanut", "peanuts", "ถั่วลิสง", "เนยถั่ว"),
    "milk": ("milk", "dairy", "cream", "butter", "cheese", "ชีส", "นม", "เนย", "ครีม"),
    "egg": ("egg", "eggs", "ไข่"),
    "gluten": ("wheat", "flour", "gluten", "แป้งสาลี", "แป้ง"),
    "shellfish": ("crab", "lobster", "clam", "oyster", "ปู", "หอย", "กั้ง"),
    "fish": ("fish", "ปลา"),
    "soy": ("soy sauce", "soy", "tofu", "เต้าหู้", "ถั่วเหลือง", "ซีอิ๊ว", "ซอสถั่วเหลือง"),
    "nut": ("almond", "cashew", "walnut", "hazelnut", "อัลมอนด์", "มะม่วงหิมพานต์"),
}
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


def assert_graph_status(resolver, expected: str, keys=None) -> None:
    """Abort unless every allergen key resolves with the expected graph_status.

    Guards against the silent-fallback failure class (MEMORY.md vLLM-LoRA entry):
    a "KG" arm that quietly fell back to the floor would compare the baseline to itself.
    """
    resolved = resolver(list(ALLERGEN_MAP if keys is None else keys))
    wrong = {key: r.graph_status for key, r in resolved.items() if r.graph_status != expected}
    if wrong:
        raise RuntimeError(f"expected graph_status={expected!r} for every key, got {wrong}")


def _is_literal(string, key):
    text = _norm(string)
    return any(_norm(t) in text for t in HISTORICAL_FLOOR_BLOCKS[key])


def _empty_by_key(keys):
    return {
        key: {
            "literal": {"positives": 0, "caught": 0},
            "derived_only": {"positives": 0, "caught": 0, "caught_2plus_hop": 0},
            "negatives": {"total": 0, "flagged": 0},
        }
        for key in keys
    }


def score_pairs(items, resolver, exclude_public: bool, *, keys=HISTORICAL_KEYS, label_version=1) -> dict:
    """Score eligible (string, allergen) pairs; v2 unresolved rows are not negatives.

    Top-level keys `literal` / `derived_only` / `negatives` are the headline strata.
    Extra breakdowns (so one seed edge or one allergen cannot pass for broad coverage):
      by_key                 -- the same strata per allergen key
      caught_by_head_edge    -- "<key>|<path joined ' -> '>" -> derived-only pairs caught via it
      spelling_note_items    -- note-bearing positive pairs: {"id", "key", "caught"} (spelling-variant
                                misses are separable from compositional misses)
      flagged_negatives      -- labeled-negative pairs the checker flagged, in whichever arm is
                                being scored (floor or floor+KG): {"id", "key"}
    NOTE: caught_2plus_hop / caught_by_head_edge mean "reported via the longest matching path",
    not "only catchable in 2+ hops" -- a shorter path may also have matched the string.
    """
    keys = tuple(keys)
    expected = set(HISTORICAL_KEYS if label_version == 1 else V2_KEYS)
    if label_version not in (1, 2) or len(keys) != len(expected) or set(keys) != expected:
        raise ValueError("label version/key set mismatch")
    for item in items:
        if not set(item["allergens"]) <= expected:
            raise ValueError("label contains an allergen outside its versioned key set")
        if label_version == 2:
            literal, derived = set(item["literal_allergens"]), set(item["derived_allergens"])
            if literal & derived or literal | derived != set(item["allergens"]):
                raise ValueError("v2 requires independently annotated literal/derived labels")
            status, reason = item.get("scoring_status"), item.get("exclusion_reason")
            if status not in ("eligible", "excluded"):
                raise ValueError("v2 scoring_status must explicitly be eligible or excluded")
            if status == "excluded" and (not isinstance(reason, str) or not reason.strip()):
                raise ValueError("v2 scoring exclusion requires a non-empty reason")
            if status == "eligible" and "exclusion_reason" in item:
                raise ValueError("v2 eligible scoring row cannot have an exclusion reason")
    scores = {
        "literal": {"positives": 0, "caught": 0, "caught_2plus_hop": 0},
        "derived_only": {"positives": 0, "caught": 0, "caught_2plus_hop": 0},
        "negatives": {"total": 0, "flagged": 0},
        "by_key": _empty_by_key(keys),
        "caught_by_head_edge": {},
        "spelling_note_items": [],
        "flagged_negatives": [],
    }
    if label_version == 2:
        scores.update(n_scored_strings=0, n_scored_pairs=0, n_excluded_strings=0, excluded_items=[])
    # One resolution per key (a closure query each), reused for every string.
    resolved_by_key = {key: resolver([key]) for key in keys}
    for item in items:
        if exclude_public and item["public"]:
            continue
        if label_version == 2:
            # ponytail: exclude whole incomplete rows; per-key unknowns only if needed later.
            if item["scoring_status"] == "excluded":
                scores["n_excluded_strings"] += 1
                scores["excluded_items"].append({"id": item["id"], "reason": item["exclusion_reason"]})
                continue
            scores["n_scored_strings"] += 1
            scores["n_scored_pairs"] += len(keys)
        for key in keys:
            v = find_allergy_violation({"adjusted_ingredients": [item["string"]]}, {}, resolved_by_key[key])
            key_scores = scores["by_key"][key]
            if key in item["allergens"]:
                literal = _is_literal(item["string"], key) if label_version == 1 else key in item["literal_allergens"]
                name = "literal" if literal else "derived_only"
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
                    scores["spelling_note_items"].append(
                        {"id": item["id"], "key": key, "caught": v is not None})
            else:
                scores["negatives"]["total"] += 1
                key_scores["negatives"]["total"] += 1
                if v is not None:
                    scores["negatives"]["flagged"] += 1
                    key_scores["negatives"]["flagged"] += 1
                    scores["flagged_negatives"].append({"id": item["id"], "key": key})
    return scores


def collision_scan(inmu_names, pool_strings, pool_public=frozenset(), db=None, keys=None):
    """KG-introduced substring hits on strings that are not (only) allergen ingredients.

    Skips a node only when it is a floor term of the SAME key it is scanned for: a floor term of
    another key that reaches this key through a KG edge is a KG-introduced match and is scanned.
    Rows are deduped on (node, allergen, matched_string); `sources` is a sorted list of the
    sources ("inmu", "pool") that contain the string; `public` is True iff the string is a pool
    string in `pool_public` (INMU-only strings are never public).
    `db` defaults to a freshly seeded in-memory graph; pass a tiny graph to test.
    """
    if db is None:
        db = make_memory_db()
        seed_allergen_graph(db)
    rows = {}
    for key in ALLERGEN_MAP if keys is None else keys:
        for entry in get_allergen_closure(db, key):
            if entry.name in FLOOR_BLOCKS[key]:
                continue
            node = _norm(entry.name)
            for source, strings in (("inmu", inmu_names), ("pool", pool_strings)):
                for s in strings:
                    if node in _norm(s):
                        row = rows.setdefault((entry.name, key, s), {
                            "node": entry.name, "allergen": key, "matched_string": s,
                            "sources": set(), "public": False,
                        })
                        row["sources"].add(source)
                        if source == "pool" and s in pool_public:
                            row["public"] = True
    return [dict(r, sources=sorted(r["sources"])) for r in rows.values()]


def load_labels(path=LABELS_PATH, *, allow_draft=False):
    path = Path(path)
    labels = json.loads(path.read_text(encoding="utf-8"))
    version = labels.get("version", 1)
    keys = tuple(labels["key_definitions"])
    expected = set(HISTORICAL_KEYS if version == 1 else V2_KEYS)
    if version not in (1, 2) or set(keys) != expected:
        raise ValueError("label version/key set mismatch")
    digest = canonical_sha256(labels)
    hash_path = path.with_suffix(".sha256")
    if version == 1 or labels.get("review_status") == "frozen" or hash_path.exists():
        committed = hash_path.read_text(encoding="utf-8").strip()
        if digest != committed:
            raise ValueError("frozen label hash mismatch")
    elif not (allow_draft and labels.get("split") == "development"):
        raise ValueError("v2 labels require user review and a frozen hash; drafts are development-only")
    return labels, version, keys, digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", default=LABELS_PATH)
    parser.add_argument("--development-draft", action="store_true")
    args = parser.parse_args(argv)
    labels, version, keys, digest = load_labels(args.labels, allow_draft=args.development_draft)
    items = labels["items"]
    if not items:
        raise RuntimeError(f"no label items in {args.labels}")
    floor_arm, kg_arm = empty_resolver(), seeded_resolver()
    assert_graph_status(floor_arm, "empty", keys)
    assert_graph_status(kg_arm, "ok", keys)
    report = {
        "label_version": version,
        "label_sha256": digest,
        "source_sha256": {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in (
            "allergen_kg/floor.py", "allergen_kg/match.py", "allergen_kg/resolve.py",
            "allergen_kg/graph.py", "database/seed_allergen_graph.py", "main.py", "eval/allergen_kg_eval.py")},
        "evaluation_kind": "current_code_regression_on_historical_labels" if version == 1 else "development_regression_not_held_out",
        "historical_baseline": "Original nine-key results remain in spec.md; this run does not replace them.",
        "key_definitions": labels["key_definitions"],
        "review_stats": labels.get("review_stats", {"review_status": labels.get("review_status")}),
    }
    for exclude_public in (False, True):
        tag = "without_public" if exclude_public else "all"
        report[tag] = {
            "n_strings": sum(1 for i in items if not (exclude_public and i["public"])),
            "floor_only": score_pairs(items, floor_arm, exclude_public, keys=keys, label_version=version),
            "floor_union_kg": score_pairs(items, kg_arm, exclude_public, keys=keys, label_version=version),
        }
    with open(INMU_PATH, encoding="utf-8") as f:
        inmu_names = [row["Thai_Name"] for row in csv.DictReader(f) if row.get("Thai_Name")]
    if not inmu_names:
        raise RuntimeError(f"no INMU names read from {INMU_PATH}")
    report["collision_hits"] = collision_scan(
        inmu_names, [i["string"] for i in items],
        pool_public={i["string"] for i in items if i["public"]}, keys=keys,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    main()
