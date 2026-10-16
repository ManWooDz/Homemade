"""Pinned N3 project-derived total; live activation requires separate approval."""
import argparse
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy.orm import Session

from nutrition import activate_reviewed_herbs as herbs
from nutrition.activate_reviewed import ROOT, _digest, _transaction, _write_rows
from nutrition.evidence import _review_valid, qualify_match
from nutrition.lookup import MacroValues, NutritionMatch

MANIFEST = "backend/nutrition/data/accepted_n3_total_records.json"
MANIFEST_SHA256 = "4bdbe4f4ecb173dd0227e35ef45f9ffba4c94dca712b6d21b084d18587955764"
METHOD = "total_by_difference_water_protein_fat_ash"
FORMULA = "100 - (water + protein + fat + ash)"
COMPONENTS = {"water": ("WATER", 1), "protein": ("PROTCNT", 1),
              "fat": ("FAT", 1), "ash": ("ASH", 2)}


def calculated_total(calculation):
    """Same-record mass balance, never a kcal inversion or available substitution."""
    if not isinstance(calculation, dict) or calculation.get("basis") != "100g" or (
        calculation.get("formula") != FORMULA or calculation.get("method") != METHOD):
        raise ValueError("invalid total calculation method/basis")
    components = calculation.get("components")
    if not isinstance(components, dict) or set(components) != set(COMPONENTS):
        raise ValueError("missing total calculation components")
    values = []
    for key, (field, page) in COMPONENTS.items():
        entry = components[key]
        if not isinstance(entry, dict) or entry.get("unit") != "g" or entry.get("basis") != "100g" or (
            entry.get("source_field") != field or type(entry.get("page")) is not int or entry["page"] != page):
            raise ValueError("invalid component definition/basis")
        value = entry.get("value")
        if not isinstance(value, str):
            raise ValueError("component requires a source decimal string")
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("invalid component value") from exc
        if not number.is_finite() or not Decimal(0) <= number <= Decimal(100):
            raise ValueError("invalid component value")
        values.append(number)
    total = Decimal(100) - sum(values)
    if not total.is_finite() or total < 0:
        raise ValueError("invalid component mass balance")
    return float(total)


def load_manifest(root=ROOT):
    root = Path(root).resolve()
    path = (root / MANIFEST).resolve()
    if not path.is_relative_to(root):
        raise ValueError("manifest outside approved root")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("approved N3 manifest changed")
    manifest = json.loads(raw)
    old = herbs.load_manifest(root)
    record = next(r for r in old["records"] if r["source_ref"] == "N3")
    review = manifest["review"]
    required = {record["artifact"], review["receipt_ref"], manifest["plan"],
                "backend/nutrition/activate_reviewed_herbs.py"}
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1 or (
        manifest["herb_manifest_sha256"] != herbs.MANIFEST_SHA256 or manifest["source"] != "INMU"
        or manifest["source_ref"] != "N3" or manifest["source_total"] is not None
        or manifest["artifact"] != record["artifact"] or not _review_valid(review)
        or not required <= manifest["artifacts"].keys()
        or manifest["artifacts"][record["artifact"]] != old["artifacts"][record["artifact"]]
        or review["receipt_sha256"] != manifest["artifacts"][review["receipt_ref"]]):
        raise ValueError("N3 policy/source binding mismatch")
    for relative, expected in manifest["artifacts"].items():
        artifact = (root / relative).resolve()
        if not artifact.is_relative_to(root) or hashlib.sha256(artifact.read_bytes()).hexdigest() != expected:
            raise ValueError("N3 review/source artifact changed")
    value = calculated_total(manifest["calculation"])
    if value != 8.08 or any(float(manifest["calculation"]["components"][key]["value"]) != record["macros"][macro]
                           for key, macro in (("protein", "protein_g"), ("fat", "fat_g"))):
        raise ValueError("N3 calculated macro mismatch")
    return manifest, old


def _states(manifest, old):
    before = herbs._desired(old)
    after = deepcopy(before)
    row = next(r for r in after["rows"] if r["source"] == "INMU" and r["source_ref"] == "N3")
    row["carbs_g"] = calculated_total(manifest["calculation"])
    derivation = row["derivation"]
    derivation["carbs_g"] = METHOD
    derivation["n3_total_calculation"] = {
        **deepcopy(manifest["calculation"]), "value": row["carbs_g"], "unit": "g",
        "origin": "project_derived", "source_total": None,
        "source_artifact": manifest["artifact"],
        "artifact_sha256": manifest["artifacts"][manifest["artifact"]],
        "review": deepcopy(manifest["review"]),
        "available_carbohydrate": 4.04, "dietary_fibre": 4.1,
        "alternative_sum": 8.14, "discrepancy_status": "unresolved",
    }
    evidence = derivation["nutrition_evidence"]
    # Rebinding retains the original identity review; it does not certify our new macro.
    evidence["row_binding"]["macros"]["carbs_g"] = row["carbs_g"]
    evidence["row_binding"]["estimate_markers"] = {"carbs_g": METHOD}
    citation = deepcopy(evidence["macros"][0]["citation"])
    citation["locator"] = "PDF pages1/2: WATER, PROTCNT, FAT, ASH; CHOCDF absent"
    evidence["macros"].append({
        "key": "carbs_g", "value": row["carbs_g"], "unit": "g", "basis": "100g",
        "definition": "carbohydrate_by_difference", "origin": "project_derived",
        "source_field": "WATER+PROTCNT+FAT+ASH (CHOCDF absent)",
        "citation": citation, "review": deepcopy(manifest["review"]),
    })
    record = next(r for r in old["records"] if r["source_ref"] == "N3")
    match = NutritionMatch(row["id"], MacroValues(**{k: row[k] for k in herbs.MACROS}),
                           row["source"], row["source_ref"], derivation, None, "100g", row["ingredient_name"])
    for alias in record["aliases"]:
        qualification = qualify_match(alias, match)
        if not qualification.identity_verified or qualification.macros_verified:
            raise ValueError("N3 must retain identity but not source-published macro qualification")
    return before, after


def preview(db, root=ROOT):
    if db.new or db.dirty or db.deleted:
        raise ValueError("preview requires a clean session")
    manifest, old = load_manifest(root)
    before, after = _states(manifest, old)
    with db.no_autoflush:
        current = herbs._state(db, old)
    if _digest(current) not in {_digest(before), _digest(after)}:
        raise ValueError("selected state differs from approved N3 transition")
    result = {"schema_version": 1, "manifest_sha256": MANIFEST_SHA256,
              "before": current, "after": after}
    result["snapshot_sha256"] = _digest(result)
    return result


def _check_snapshot(snapshot, manifest, old):
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "schema_version", "manifest_sha256", "before", "after", "snapshot_sha256"}:
        raise ValueError("invalid N3 snapshot shape")
    payload = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    if type(snapshot["schema_version"]) is not int or snapshot["schema_version"] != 1 or (
        snapshot["manifest_sha256"] != MANIFEST_SHA256 or _digest(payload) != snapshot["snapshot_sha256"]):
        raise ValueError("N3 snapshot digest/version mismatch")
    before, after = _states(manifest, old)
    if _digest(snapshot["after"]) != _digest(after) or _digest(snapshot["before"]) not in {
        _digest(before), _digest(after)}:
        raise ValueError("snapshot is not the approved N3 transition")


def _write_n3(db, state):
    _write_rows(db, {"rows": [r for r in state["rows"] if r["source"] == "INMU" and r["source_ref"] == "N3"]})


def apply_snapshot(db, snapshot, root=ROOT):
    manifest, old = load_manifest(root)
    _check_snapshot(snapshot, manifest, old)
    with _transaction(db):
        current = herbs._state(db, old)
        if _digest(current) == _digest(snapshot["after"]):
            return "noop"
        if _digest(current) != _digest(snapshot["before"]):
            raise ValueError("N3 state changed since reviewed preview")
        _write_n3(db, snapshot["after"])
        db.flush()
        load_manifest(root)
        if _digest(herbs._state(db, old)) != _digest(snapshot["after"]):
            raise ValueError("N3 post-write state mismatch")
    return "applied"


def restore_snapshot(db, snapshot, root=ROOT):
    manifest, old = load_manifest(root)
    _check_snapshot(snapshot, manifest, old)
    before, _ = _states(manifest, old)
    if _digest(snapshot["before"]) != _digest(before):
        raise ValueError("restore requires the original N3 transition snapshot")
    with _transaction(db):
        if _digest(herbs._state(db, old)) != _digest(snapshot["after"]):
            raise ValueError("cannot restore N3 over later changes")
        _write_n3(db, before)
        db.flush()
        load_manifest(root)
        if _digest(herbs._state(db, old)) != _digest(before):
            raise ValueError("N3 post-restore state mismatch")
    return "restored"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-env", required=True, help="Explicit target URL env variable; never printed")
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--apply-snapshot", type=Path)
    operation.add_argument("--restore-snapshot", type=Path)
    args = parser.parse_args(argv)
    url = os.environ.get(args.database_url_env)
    if not url:
        parser.error("explicit database URL environment variable is missing")
    engine = None
    try:
        load_manifest()
        from sqlalchemy import create_engine
        engine = create_engine(url)
        if engine.dialect.name != "postgresql":
            raise ValueError("CLI requires explicitly configured PostgreSQL")
        with Session(engine, autoflush=False) as db:
            if args.apply_snapshot or args.restore_snapshot:
                snapshot = json.loads((args.apply_snapshot or args.restore_snapshot).read_text(encoding="utf-8"))
                action = apply_snapshot if args.apply_snapshot else restore_snapshot
                print(json.dumps({"status": action(db, snapshot)}))
            else:
                db.connection().exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                print(json.dumps(preview(db), ensure_ascii=True, indent=2, allow_nan=False))
                db.rollback()
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
