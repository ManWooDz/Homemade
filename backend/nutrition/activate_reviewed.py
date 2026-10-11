"""Bounded C2 preview/apply; no source fetch, seed, startup hook or implicit DB URL."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from database.models import IngredientNutrition, IngredientNutritionAlias
from nutrition.evidence import qualify_match
from nutrition.lookup import MacroValues, NutritionMatch
from nutrition.text import normalize_alias
from nutrition.units import is_nonnegative_finite

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "backend/nutrition/data/accepted_c2_records.json"
MANIFEST_SHA256 = "5164fb436d8904e6eadbb96da58a4e4a2dee8ac063d931c2df47d3a0bddbb115"
FIELDS = ("id", "source", "source_ref", "ingredient_name", "unit_basis",
          "calories", "protein_g", "carbs_g", "fat_g", "portion_grams", "derivation")
MACROS = {"calories": ("kcal", "energy", "ENERCT", 1),
          "protein_g": ("g", "protein", "PROTCNT", 1),
          "carbs_g": ("g", "total_carbohydrate", "CHOCDF", 2),
          "fat_g": ("g", "total_fat", "FAT", 1)}


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def load_manifest(root=ROOT):
    """Pin the approved file and its retained artifacts, not arbitrary user JSON."""
    root = Path(root).resolve()
    raw = (root / MANIFEST).read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("approved manifest hash mismatch")
    manifest = json.loads(raw)
    for relative, expected in manifest["artifacts"].items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("review/source artifact verification failed")
    if {r["source_ref"] for r in manifest["records"]} != {"N2", "N26", "A11"}:
        raise ValueError("target allowlist mismatch")
    return manifest


def _state(db, manifest, lock=False):
    records = manifest["records"]
    query = db.query(IngredientNutrition).filter(
        IngredientNutrition.source == "INMU",
        IngredientNutrition.source_ref.in_([r["source_ref"] for r in records]))
    if lock:
        query = query.with_for_update()
    rows = query.populate_existing().all()
    ordered = []
    for record in records:
        matches = [r for r in rows if r.source_ref == record["source_ref"]]
        if len(matches) != 1 or matches[0].ingredient_name != record["ingredient_name"]:
            raise ValueError("missing, duplicate or mismatched target: " + record["source_ref"])
        ordered.append(matches[0])
    approved = {normalize_alias(a) for r in records for a in r["aliases"]}
    query = db.query(IngredientNutritionAlias).filter(or_(
        IngredientNutritionAlias.ingredient_nutrition_id.in_([r.id for r in ordered]),
        IngredientNutritionAlias.alias.in_(sorted(approved))))
    if lock:
        query = query.with_for_update()
    aliases = [{"alias": a.alias, "owner": a.ingredient_nutrition_id}
               for a in query.populate_existing().all()]
    return {"rows": [{k: deepcopy(getattr(r, k)) for k in FIELDS} for r in ordered],
            "aliases": sorted(aliases, key=lambda a: a["alias"])}


def _evidence(row, record, manifest):
    review = deepcopy(manifest["review"])
    citation = {"publisher": "Institute of Nutrition, Mahidol University, Thailand",
                "source": "INMU", "source_ref": record["source_ref"],
                "release": "Thai FCD Online version 2, September 2018 (export footer citation)",
                "url": record["url"], "artifact_sha256": manifest["artifacts"][record["artifact"]],
                "locator": "PDF page 1, food code/name and preparation",
                "extraction": "User-supplied publisher export; all pages text-extracted and visually reviewed; URL association user supplied"}
    entries = []
    for key, (unit, definition, field, page) in MACROS.items():
        entry = {"key": key, "value": row[key], "unit": unit, "basis": "100g",
                 "definition": definition, "origin": "source_published", "source_field": field,
                 "citation": {**citation, "locator": f"PDF page {page}, {field} row, Content per 100 g of food"},
                 "review": deepcopy(review)}
        if key == "calories":
            entry["publisher_method"] = "Published ENERCT: 4*protein + 9*fat + 4*CHOCDF; retain source integer energy"
        elif key == "carbs_g":
            entry["publisher_method"] = "Published CHOCDF: 100g minus water, protein, fat and ash; total, not available carbohydrate"
        entries.append(entry)
    return {"schema_version": 1, "review": review,
            "row_binding": {"source": row["source"], "source_ref": row["source_ref"],
                            "ingredient_name": row["ingredient_name"], "unit_basis": row["unit_basis"],
                            "macros": {k: row[k] for k in MACROS},
                            "portion_grams": deepcopy(row["portion_grams"] or {}), "estimate_markers": {}},
            "identity": [{"alias": normalize_alias(a), "relation": "exact",
                          "ingredient_name": row["ingredient_name"], "preparation": record["preparation"],
                          "rationale": "Explicit alias/preparation approved in the bounded C2 implementation scope",
                          "citation": deepcopy(citation), "review": deepcopy(review)} for a in record["aliases"]],
            "macros": entries, "portions": []}


def _desired(before, manifest):
    if set(before) != {"rows", "aliases"} or len(before["rows"]) != len(manifest["records"]):
        raise ValueError("invalid selected state shape")
    if len({r["id"] for r in before["rows"]}) != len(before["rows"]) or (
        len({a["alias"] for a in before["aliases"]}) != len(before["aliases"])):
        raise ValueError("duplicate snapshot row/alias")
    after = deepcopy(before)
    owners = {a["alias"]: a["owner"] for a in before["aliases"]}
    for row, record in zip(after["rows"], manifest["records"]):
        if set(row) != set(FIELDS) or type(row["id"]) is not int or row["id"] <= 0 or any(
            row[k] != record[k] for k in ("source", "source_ref", "ingredient_name")):
            raise ValueError("snapshot target identity mismatch")
        if row["unit_basis"] != "100g" or any(
            not is_nonnegative_finite(row[k]) or row[k] != record["macros"][k]
            for k in ("protein_g", "carbs_g", "fat_g")):
            raise ValueError("target macro/basis drift: " + record["source_ref"])
        derivation = row["derivation"]
        if derivation is not None and not isinstance(derivation, dict):
            raise ValueError("malformed derivation")
        derivation = deepcopy(derivation or {})
        if "proxy" in derivation or "carbs_g" in derivation:
            raise ValueError("unexpected proxy/carbohydrate marker")
        energy = row["calories"]
        if not is_nonnegative_finite(energy):
            raise ValueError("missing or invalid current energy")
        if "energy_kcal" in derivation:
            if derivation["energy_kcal"] != "atwater" or not math.isclose(
                energy, record["legacy_energy"], rel_tol=0, abs_tol=1e-9):
                raise ValueError("unexpected energy derivation/value")
            derivation.pop("energy_kcal")
        elif energy != record["macros"]["calories"]:
            raise ValueError("unmarked current energy differs from accepted source")
        for k, value in record["macros"].items():
            row[k] = float(value)
        evidence = _evidence(row, record, manifest)
        if "nutrition_evidence" in derivation and _digest(derivation["nutrition_evidence"]) != _digest(evidence):
            raise ValueError("unexpected or stale existing evidence")
        derivation["nutrition_evidence"] = evidence
        row["derivation"] = derivation
        match = NutritionMatch(row["id"], MacroValues(**{k: row[k] for k in MACROS}),
                               row["source"], row["source_ref"], derivation,
                               row["portion_grams"], row["unit_basis"], row["ingredient_name"])
        for alias in record["aliases"]:
            alias = normalize_alias(alias)
            if alias in owners and owners[alias] != row["id"]:
                raise ValueError("approved alias belongs to another row")
            qualification = qualify_match(alias, match)
            if not qualification.identity_verified or not qualification.macros_verified:
                raise ValueError("proposed evidence failed C1 qualification")
            owners[alias] = row["id"]
    after["aliases"] = [{"alias": a, "owner": owners[a]} for a in sorted(owners)]
    return after


def preview(db, root=ROOT, *, lock=False):
    """Read-only; reject pending writes rather than letting a SELECT autoflush them."""
    if db.new or db.dirty or db.deleted:
        raise ValueError("preview requires a clean session")
    manifest = load_manifest(root)
    with db.no_autoflush:
        before = _state(db, manifest, lock)
        after = _desired(before, manifest)
    result = {"schema_version": 1, "manifest_sha256": MANIFEST_SHA256,
              "before": before, "after": after}
    result["snapshot_sha256"] = _digest(result)
    return result


def _check_snapshot(snapshot):
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "schema_version", "manifest_sha256", "before", "after", "snapshot_sha256"}:
        raise ValueError("invalid snapshot shape")
    payload = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    if type(snapshot["schema_version"]) is not int or snapshot["schema_version"] != 1 or (
        snapshot["manifest_sha256"] != MANIFEST_SHA256 or _digest(payload) != snapshot["snapshot_sha256"]):
        raise ValueError("snapshot digest/version mismatch")


@contextmanager
def _transaction(db):
    if db.in_transaction() or db.new or db.dirty or db.deleted:
        raise ValueError("write requires a clean session without an open transaction")
    dialect = db.get_bind().dialect.name
    if dialect not in ("postgresql", "sqlite"):
        raise ValueError("unsupported activation database")
    with db.begin():
        if dialect == "sqlite":
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        else:
            # Row locks alone cannot guard new aliases or duplicate source/ref inserts.
            db.connection().exec_driver_sql("SET LOCAL lock_timeout = '5s'")
            db.connection().exec_driver_sql(
                "LOCK TABLE ingredient_nutrition, ingredient_nutrition_aliases IN SHARE ROW EXCLUSIVE MODE")
        yield


def _write_rows(db, state):
    for saved in state["rows"]:
        row = db.get(IngredientNutrition, saved["id"], populate_existing=True)
        for key in FIELDS:
            if key != "id":
                setattr(row, key, deepcopy(saved[key]))


def apply_snapshot(db, snapshot, root=ROOT):
    """Explicit atomic apply; caller must obtain live-write approval separately."""
    _check_snapshot(snapshot)
    with _transaction(db):
        current = preview(db, root, lock=True)
        if _digest(current["before"]) == _digest(snapshot["after"]):
            return "noop"
        if _digest(current["before"]) != _digest(snapshot["before"]) or (
            _digest(current["after"]) != _digest(snapshot["after"])):
            raise ValueError("selected state changed since reviewed preview")
        _write_rows(db, current["after"])
        old_aliases = {a["alias"] for a in current["before"]["aliases"]}
        for alias in current["after"]["aliases"]:
            if alias["alias"] not in old_aliases:
                db.add(IngredientNutritionAlias(alias=alias["alias"], ingredient_nutrition_id=alias["owner"]))
        db.flush()
        if _digest(_state(db, load_manifest(root), lock=True)) != _digest(current["after"]):
            raise ValueError("post-write state mismatch")
    return "applied"


def restore_snapshot(db, snapshot, root=ROOT):
    """Explicit guarded restoration; newly added aliases stay numerical-only, not deleted."""
    _check_snapshot(snapshot)
    manifest = load_manifest(root)
    with _transaction(db):
        current = _state(db, manifest, lock=True)
        if _digest(current) != _digest(snapshot["after"]):
            raise ValueError("cannot restore over later changes")
        # Reconstruct the approved transition before trusting a caller-supplied before-state.
        if _digest(_desired(snapshot["before"], manifest)) != _digest(snapshot["after"]):
            raise ValueError("snapshot is not an approved transition")
        _write_rows(db, snapshot["before"])
        db.flush()
        expected = {"rows": snapshot["before"]["rows"], "aliases": snapshot["after"]["aliases"]}
        if _digest(_state(db, manifest, lock=True)) != _digest(expected):
            raise ValueError("post-restore state mismatch")
    return "restored_rows_aliases_retained"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-env", required=True, help="Explicit env variable holding the target URL; never printed")
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--apply-snapshot", type=Path)
    operation.add_argument("--restore-snapshot", type=Path)
    args = parser.parse_args(argv)
    from sqlalchemy import create_engine
    url = os.environ.get(args.database_url_env)
    if not url:
        parser.error("explicit database URL environment variable is missing")
    engine = None
    try:
        engine = create_engine(url)
        # The CLI targets the project's PostgreSQL deployment; SQLite is only an injected test Session.
        if engine.dialect.name != "postgresql":
            raise ValueError("CLI requires an explicitly configured PostgreSQL database")
        with Session(engine) as db:
            if args.apply_snapshot or args.restore_snapshot:
                snapshot = json.loads((args.apply_snapshot or args.restore_snapshot).read_text(encoding="utf-8"))
                operation = apply_snapshot if args.apply_snapshot else restore_snapshot
                print(json.dumps({"status": operation(db, snapshot)}))
            else:
                print(json.dumps(preview(db), ensure_ascii=True, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        # Driver exceptions may contain credentials/SQL; expose only a safe failure category.
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
