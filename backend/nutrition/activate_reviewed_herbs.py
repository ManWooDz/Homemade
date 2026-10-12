"""Pinned three-herb preview; apply/restore require separate live-write approval."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from database.models import IngredientNutrition, IngredientNutritionAlias
from nutrition.activate_reviewed import ROOT, FIELDS, _digest, _transaction, _write_rows
from nutrition.evidence import qualify_match
from nutrition.lookup import MacroValues, NutritionMatch
from nutrition.text import normalize_alias
from nutrition.units import is_nonnegative_finite

MANIFEST = "backend/nutrition/data/accepted_herb_records.json"
MANIFEST_SHA256 = "6bffa178fc3c0328468e210942693e708b16668f28c5ba5ab3d1c5519c1c9436"
HELPER = "backend/nutrition/activate_reviewed.py"
MACROS = {"calories": ("kcal", "energy", 1), "protein_g": ("g", "protein", 1),
          "carbs_g": ("g", "total_carbohydrate", 2), "fat_g": ("g", "total_fat", 1)}


def load_manifest(root=ROOT):
    """Only the byte-pinned reviewed bundle, never a caller-supplied manifest."""
    root = Path(root).resolve()
    path = (root / MANIFEST).resolve()
    if not path.is_relative_to(root):
        raise ValueError("manifest outside approved root")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("approved herb manifest changed")
    manifest = json.loads(raw)
    records = manifest["records"]
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1 or (
        len(records) != 3 or [r["source_ref"] for r in records] != ["N11", "N3", "N35"]
        or any(r["source"] != "INMU" for r in records)):
        raise ValueError("herb target allowlist mismatch")
    required = {HELPER, manifest["inventory"], manifest["review"]["receipt_ref"],
                *(r["artifact"] for r in records)}
    if not required <= manifest["artifacts"].keys() or (
        manifest["review"]["receipt_sha256"] != manifest["artifacts"][manifest["review"]["receipt_ref"]]):
        raise ValueError("incomplete review/source pins")
    artifacts = {}
    for relative, expected in manifest["artifacts"].items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("artifact outside approved root")
        artifacts[relative] = path.read_bytes()
        if hashlib.sha256(artifacts[relative]).hexdigest() != expected:
            raise ValueError("herb review/source artifact changed")
    inventory = [json.loads(line) for line in artifacts[manifest["inventory"]].splitlines()]
    if len(inventory) != 6 or inventory[0]["readonly"] != "on" or (
        inventory[0]["isolation"] != "repeatable read" or len(inventory[3]["rows"]) != 6
        or len(inventory[3]["aliases"]) != 9):
        raise ValueError("original inventory shape mismatch")
    saved = inventory[3]
    manifest["before"] = {
        "rows": [{k: deepcopy(row[k]) for k in FIELDS} for row in sorted(saved["rows"], key=lambda r: r["id"])],
        "aliases": sorted([{"alias": a["alias"], "owner": a["ingredient_nutrition_id"]}
                           for a in saved["aliases"]], key=lambda a: a["alias"])}
    manifest["alias_ids"] = {a["alias"]: a["id"] for a in saved["aliases"]}
    before = manifest["before"]
    # PostgreSQL row_to_json may print Float41.0 as41; bind ORM Float semantics without rewriting evidence bytes.
    for row in before["rows"]:
        for key in MACROS:
            if row[key] is not None:
                if not is_nonnegative_finite(row[key]):
                    raise ValueError("invalid original macro")
                row[key] = float(row[key])
    pairs = [(r["source"], r["source_ref"]) for r in before["rows"]]
    expected_pairs = [("INMU", r["source_ref"]) for r in records] + [("USDA", r["proxy_source_ref"]) for r in records]
    aliases = [normalize_alias(a) for r in records for a in r["aliases"]]
    if sorted(pairs) != sorted(expected_pairs) or len({r["id"] for r in before["rows"]}) != 6 or (
        len(manifest["alias_ids"]) != 9 or len(set(aliases)) != 13
        or any(a != normalize_alias(a) for a in manifest["alias_ids"])):
        raise ValueError("original rows/aliases mismatch")
    return manifest


def _state(db, manifest):
    original = manifest["before"]
    rows = db.query(IngredientNutrition).filter(or_(
        *[(IngredientNutrition.source == r["source"]) & (IngredientNutrition.source_ref == r["source_ref"])
          for r in original["rows"]])).populate_existing().all()
    if len(rows) != 6:
        raise ValueError("missing or duplicate herb/proxy row")
    by_id = {r.id: r for r in rows}
    for saved in original["rows"]:
        row = by_id.get(saved["id"])
        if row is None or any(getattr(row, k) != saved[k] for k in ("source", "source_ref", "ingredient_name")):
            raise ValueError("selected row identity changed")
    approved = {normalize_alias(a) for r in manifest["records"] for a in r["aliases"]}
    aliases = db.query(IngredientNutritionAlias).filter(or_(
        IngredientNutritionAlias.ingredient_nutrition_id.in_(by_id),
        IngredientNutritionAlias.alias.in_(sorted(approved)))).populate_existing().all()
    ids = {a.alias: a.id for a in aliases}
    if any(ids.get(alias) != alias_id for alias, alias_id in manifest["alias_ids"].items()):
        raise ValueError("original alias ID changed")
    return {"rows": [{k: deepcopy(getattr(by_id[r["id"]], k)) for k in FIELDS} for r in original["rows"]],
            "aliases": sorted([{"alias": a.alias, "owner": a.ingredient_nutrition_id} for a in aliases],
                              key=lambda a: a["alias"])}


def _evidence(row, record, manifest):
    review = deepcopy(manifest["review"])
    citation = {"publisher": "Institute of Nutrition, Mahidol University, Thailand",
                "source": "INMU", "source_ref": record["source_ref"],
                "release": "Thai FCD Online version 2, September 2018 (export footer citation)",
                "url": record["url"], "artifact_sha256": manifest["artifacts"][record["artifact"]],
                "locator": "PDF page 1, food code/name/scientific name; further preparation not specified",
                "extraction": "Original user-supplied export, all pages visually reviewed; URL association user supplied, live page inaccessible"}
    fields = {"calories": record["energy_field"], "protein_g": "PROTCNT", "carbs_g": "CHOCDF", "fat_g": "FAT"}
    entries = []
    for key, (unit, definition, page) in MACROS.items():
        if row[key] is None:
            continue
        entry = {"key": key, "value": row[key], "unit": unit, "basis": "100g",
                 "definition": definition, "origin": "source_published", "source_field": fields[key],
                 "citation": {**citation, "locator": f"PDF page {page}, {fields[key]} row, Content per 100 g of food"},
                 "review": deepcopy(review)}
        if key == "calories":
            entry["publisher_method"] = ("Published ENERCT using protein/fat/CHOCDF; retain source integer, not project Atwater"
                                         if fields[key] == "ENERCT" else "Published ENERC; retain displayed source energy, not project completion")
        elif key == "carbs_g":
            entry["publisher_method"] = "Published CHOCDF by difference; total, not available carbohydrate"
        entries.append(entry)
    return {"schema_version": 1, "review": review,
            "row_binding": {"source": row["source"], "source_ref": row["source_ref"],
                            "ingredient_name": row["ingredient_name"], "unit_basis": row["unit_basis"],
                            "macros": {k: row[k] for k in MACROS}, "portion_grams": {}, "estimate_markers": {}},
            "identity": [{"alias": normalize_alias(alias), "relation": "exact", "ingredient_name": row["ingredient_name"],
                          "preparation": record["preparation"], "rationale": "Bounded plain named ingredient convention and leaf-specific allowlist explicitly approved",
                          "citation": deepcopy(citation), "review": deepcopy(review)} for alias in record["aliases"]],
            "macros": entries, "portions": []}


def _desired(manifest):
    after = deepcopy(manifest["before"])
    owners = {a["alias"]: a["owner"] for a in after["aliases"]}
    for record in manifest["records"]:
        row = next(r for r in after["rows"] if r["source"] == "INMU" and r["source_ref"] == record["source_ref"])
        proxy = next(r for r in after["rows"] if r["source"] == "USDA" and r["source_ref"] == record["proxy_source_ref"])
        marker = "carbs_g" if record["source_ref"] == "N3" else "energy_kcal"
        expected = {marker: "by_difference" if marker == "carbs_g" else "atwater"}
        if row["ingredient_name"] != record["ingredient_name"] or row["unit_basis"] != "100g" or (
            row["portion_grams"] is not None or row["derivation"] != expected or "proxy" not in (proxy["derivation"] or {})):
            raise ValueError("unexpected legacy row/derivation/portion")
        if any(row[k] != record["macros"][k] for k in ("protein_g", "fat_g")) or (
            record["source_ref"] == "N3" and record["macros"]["carbs_g"] is not None):
            raise ValueError("source macro mismatch")
        correction = {"schema_version": 1, "review": deepcopy(manifest["review"]),
                      "before_macros": {k: row[k] for k in MACROS}, "before_derivation": deepcopy(row["derivation"]),
                      "source_artifact": record["artifact"], "artifact_sha256": manifest["artifacts"][record["artifact"]],
                      "reason": "Replace Homemade completion with published source field or documented source absence",
                      "identity_limits": record["preparation"]}
        if "available_carbohydrate" in record:
            correction["available_carbohydrate_not_total"] = deepcopy(record["available_carbohydrate"])
        row.update({k: float(v) if v is not None and is_nonnegative_finite(v) else v
                    for k, v in record["macros"].items()})
        row["derivation"] = {"herb_source_correction": correction, "nutrition_evidence": _evidence(row, record, manifest)}
        for alias in record["aliases"]:
            alias = normalize_alias(alias)
            expected_owner = proxy["id"] if alias == record["remap_alias"] else None if alias in record["new_aliases"] else row["id"]
            if owners.get(alias) != expected_owner:
                raise ValueError("approved original alias ownership mismatch")
            owners[alias] = row["id"]
            qualification = qualify_match(alias, NutritionMatch(row["id"], MacroValues(**{k: row[k] for k in MACROS}),
                row["source"], row["source_ref"], row["derivation"], None, "100g", row["ingredient_name"]))
            if not qualification.identity_verified or qualification.macros_verified != (record["source_ref"] != "N3") or (
                qualification.verified_portion_grams):
                raise ValueError("proposed herb qualification mismatch")
    after["aliases"] = [{"alias": alias, "owner": owners[alias]} for alias in sorted(owners)]
    return after


def preview(db, root=ROOT):
    if db.new or db.dirty or db.deleted:
        raise ValueError("preview requires a clean session")
    manifest = load_manifest(root)
    with db.no_autoflush:
        before, after = _state(db, manifest), _desired(manifest)
    if _digest(before) not in {_digest(manifest["before"]), _digest(after)}:
        raise ValueError("selected state differs from approved herb transition")
    result = {"schema_version": 1, "manifest_sha256": MANIFEST_SHA256, "before": before, "after": after}
    result["snapshot_sha256"] = _digest(result)
    return result


def _check_snapshot(snapshot, manifest):
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "schema_version", "manifest_sha256", "before", "after", "snapshot_sha256"}:
        raise ValueError("invalid herb snapshot shape")
    if type(snapshot["schema_version"]) is not int or snapshot["schema_version"] != 1 or (
        snapshot["manifest_sha256"] != MANIFEST_SHA256 or _digest({k: v for k, v in snapshot.items() if k != "snapshot_sha256"}) != snapshot["snapshot_sha256"]):
        raise ValueError("herb snapshot digest/version mismatch")
    desired = _desired(manifest)
    if _digest(snapshot["after"]) != _digest(desired) or _digest(snapshot["before"]) not in {
        _digest(manifest["before"]), _digest(desired)}:
        raise ValueError("snapshot is not the approved herb transition")


def _write(db, state):
    # Proxy rows are comparison controls, never write targets.
    _write_rows(db, {"rows": [r for r in state["rows"] if r["source"] == "INMU"]})
    for saved in state["aliases"]:
        alias = db.query(IngredientNutritionAlias).filter_by(alias=saved["alias"]).one_or_none()
        if alias is None:
            db.add(IngredientNutritionAlias(alias=saved["alias"], ingredient_nutrition_id=saved["owner"]))
        elif alias.ingredient_nutrition_id != saved["owner"]:
            alias.ingredient_nutrition_id = saved["owner"]


def apply_snapshot(db, snapshot, root=ROOT):
    manifest = load_manifest(root)
    _check_snapshot(snapshot, manifest)
    with _transaction(db):
        current = _state(db, manifest)
        if _digest(current) == _digest(snapshot["after"]):
            return "noop"
        if _digest(current) != _digest(snapshot["before"]):
            raise ValueError("herb state changed since reviewed preview")
        _write(db, snapshot["after"])
        db.flush()
        load_manifest(root)
        if _digest(_state(db, manifest)) != _digest(snapshot["after"]):
            raise ValueError("herb post-write state mismatch")
    return "applied"


def restore_snapshot(db, snapshot, root=ROOT):
    manifest = load_manifest(root)
    _check_snapshot(snapshot, manifest)
    if _digest(snapshot["before"]) != _digest(manifest["before"]):
        raise ValueError("restore requires the original transition snapshot")
    expected = deepcopy(snapshot["before"])
    original_aliases = {a["alias"] for a in expected["aliases"]}
    expected["aliases"] = sorted(expected["aliases"] + [deepcopy(a) for a in snapshot["after"]["aliases"]
                                                      if a["alias"] not in original_aliases], key=lambda a: a["alias"])
    with _transaction(db):
        if _digest(_state(db, manifest)) != _digest(snapshot["after"]):
            raise ValueError("cannot restore herbs over later changes")
        _write(db, expected)
        db.flush()
        load_manifest(root)
        if _digest(_state(db, manifest)) != _digest(expected):
            raise ValueError("herb post-restore state mismatch")
    return "restored_rows_and_owners_new_aliases_retained"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-env", required=True, help="Explicit target URL environment variable; never printed")
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
        # Driver exceptions may include credentials or SQL; expose the category only.
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
