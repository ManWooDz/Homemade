"""One approved G4 correction; preview by default, live apply separately gated."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy.orm import Session

from nutrition.activate_reviewed import ROOT, _digest, _state, _transaction, _write_rows
from nutrition.evidence import qualify_match
from nutrition.lookup import MacroValues, NutritionMatch

PACKET = "docs/nutrition-source-qa/2026-10-12/g4-preview-01/"
SOURCE = "docs/nutrition-source-qa/2026-10-11/user-supplied-08/G4.pdf"
RECEIPT = PACKET + "implementation-approval.md"
ARTIFACTS = {
    RECEIPT: "e9fae93fa377ecf533e839cbd78ef7fb61f21697c140525cff52e39b2af64b73",
    PACKET + "review.md": "1378651a80b167dbe6ee32ba42bfe5dbe982c215e474d935180092e48996deb4",
    PACKET + "current-state.json": "08d1a745671394a3f3446f60466c328374f0d21f7eb5e4329462a23d01245b96",
    SOURCE: "8433e363126f946f1f9c907c4ebf7a7a08e0849486ff42aada6194c8a1a45762",
    "backend/nutrition/activate_reviewed.py": "0c6607568837154ef23d85bb700883f99b5d094cdb755f1f9a3c9fc4cde43684",
}
BEFORE_SHA256 = "1203663501f8c276d9087ef2d142fbc10934789d3edc8b648edc28f619f349a7"
EXACT_ALIASES = ("กุ้งก้ามกราม, สด", "prawn, giant freshwater, raw")
SELECTION = {"records": [{"source_ref": "G4", "ingredient_name": "กุ้งก้ามกราม, สด",
                          "aliases": [*EXACT_ALIASES, "กุ้ง"]}]}
REVIEW = {"status": "accepted", "reviewer": "ratchanon", "reviewed_at_utc": "2026-10-11T17:58:58Z",
          "receipt_ref": RECEIPT, "receipt_sha256": ARTIFACTS[RECEIPT]}


def _approved_before(root):
    root = Path(root).resolve()
    raw = {}
    for relative, expected in ARTIFACTS.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("artifact outside approved root")
        raw[relative] = path.read_bytes()
        if hashlib.sha256(raw[relative]).hexdigest() != expected:
            raise ValueError("G4 approved artifact changed")
    before = json.loads(raw[PACKET + "current-state.json"])["state"]
    if _digest(before) != BEFORE_SHA256:
        raise ValueError("G4 original binding mismatch")
    return before


def _desired(before):
    if _digest(before) != BEFORE_SHA256:
        raise ValueError("G4 original state changed")
    after = deepcopy(before)
    row = after["rows"][0]
    row["calories"], row["carbs_g"] = 108.0, None
    citation = {"publisher": "Institute of Nutrition, Mahidol University, Thailand",
                "source": "INMU", "source_ref": "G4",
                "release": "Thai FCD Online version 2, September 2018 (export footer citation)",
                "url": "https://inmu.mahidol.ac.th/thaifcd//foodsearch/food_name/?dbcode=STD&food_group_id=77&id=1037&name=Prawn,%20giant%20freshwater,%20raw",
                "artifact_sha256": ARTIFACTS[SOURCE], "locator": "PDF page 1, G4 identity and raw preparation",
                "extraction": "User-supplied publisher export, all pages reviewed; URL association user supplied"}
    macros = {k: row[k] for k in ("calories", "protein_g", "carbs_g", "fat_g")}
    entries = [{"key": key, "value": row[key], "unit": unit, "basis": "100g",
                "definition": definition, "origin": "source_published", "source_field": field,
                "citation": {**citation, "locator": f"PDF page 1, {field}, Content per 100 g of food"},
                "review": deepcopy(REVIEW)}
               for key, unit, definition, field in (
                   ("calories", "kcal", "energy", "ENERC"),
                   ("protein_g", "g", "protein", "PROTCNT"), ("fat_g", "g", "total_fat", "FAT"))]
    entries[0]["publisher_method"] = "Published ENERC: 4*protein + 9*fat + 4*CHOAVLDF + 2*fibre, excluding alcohol; retain displayed108"
    evidence = {"schema_version": 1, "review": deepcopy(REVIEW),
                "row_binding": {"source": "INMU", "source_ref": "G4", "ingredient_name": row["ingredient_name"],
                                "unit_basis": "100g", "macros": macros, "portion_grams": {}, "estimate_markers": {}},
                "identity": [{"alias": alias, "relation": "exact", "ingredient_name": row["ingredient_name"],
                              "preparation": "giant freshwater prawn, raw (Macrobrachium rosenbergii)",
                              "rationale": "Existing descriptive alias matches the reviewed G4 identity and preparation",
                              "citation": deepcopy(citation), "review": deepcopy(REVIEW)} for alias in EXACT_ALIASES],
                "macros": entries, "portions": []}
    row["derivation"] = {
        "nutrition_evidence": evidence,
        "g4_correction": {
            "before_state_ref": PACKET + "current-state.json", "before_state_sha256": BEFORE_SHA256,
            "before_file_sha256": ARTIFACTS[PACKET + "current-state.json"],
            "previous_macros": {k: before["rows"][0][k] for k in macros},
            "previous_derivation": deepcopy(before["rows"][0]["derivation"]),
            "removed_estimate_method": "(energy - 4*protein - 9*fat)/4, clamped to zero when negative",
            "decision": "Copy source ENERC; remove obsolete clamped total carbohydrate. CHOCDF is missing, not zero.",
            "review": deepcopy(REVIEW),
            "available_carbohydrate_observation": {
                "source_field": "CHOAVLDF", "definition": "available_carbohydrate", "value": 0.80,
                "unit": "g", "basis": "100g", "origin": "source_published",
                "citation": {**citation, "locator": "PDF page 1 CHOAVLDF; page 2 missing total CHOCDF"},
                "review": deepcopy(REVIEW)}}}
    match = NutritionMatch(row["id"], MacroValues(**macros), "INMU", "G4", row["derivation"],
                           row["portion_grams"], "100g", row["ingredient_name"])
    for alias in EXACT_ALIASES:
        qualified = qualify_match(alias, match)
        if not qualified.identity_verified or qualified.macros_verified or qualified.verified_portion_grams:
            raise ValueError("G4 partial evidence failed qualification")
    if qualify_match("กุ้ง", match).identity_verified:
        raise ValueError("generic shrimp identity must remain unqualified")
    return after


def preview(db, root=ROOT, *, lock=False):
    if db.new or db.dirty or db.deleted:
        raise ValueError("preview requires a clean session")
    before = _approved_before(root)
    after = _desired(before)
    with db.no_autoflush:
        current = _state(db, SELECTION, lock)
    if _digest(current) not in (_digest(before), _digest(after)):
        raise ValueError("G4 current binding changed")
    result = {"schema_version": 1, "operation": "G4-source-correction",
              "approval_sha256": ARTIFACTS[RECEIPT], "before": current, "after": after}
    result["snapshot_sha256"] = _digest(result)
    return result


def _check_snapshot(snapshot, root):
    if not isinstance(snapshot, dict) or set(snapshot) != {
        "schema_version", "operation", "approval_sha256", "before", "after", "snapshot_sha256"}:
        raise ValueError("invalid G4 snapshot shape")
    payload = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    if type(snapshot["schema_version"]) is not int or snapshot["schema_version"] != 1 or (
        snapshot["operation"] != "G4-source-correction" or snapshot["approval_sha256"] != ARTIFACTS[RECEIPT]
        or _digest(payload) != snapshot["snapshot_sha256"]):
        raise ValueError("invalid G4 snapshot digest/version")
    original = _approved_before(root)
    after = _desired(original)
    if _digest(snapshot["after"]) != _digest(after) or _digest(snapshot["before"]) not in (
        _digest(original), _digest(after)):
        raise ValueError("G4 snapshot is not the approved transition")


def apply_snapshot(db, snapshot, root=ROOT):
    """Caller must obtain separate live-write approval for the fresh snapshot."""
    _check_snapshot(snapshot, root)
    with _transaction(db):
        if db.get_bind().dialect.name == "postgresql":
            db.connection().exec_driver_sql("SET LOCAL statement_timeout = '5s'")
        current = preview(db, root, lock=True)
        if _digest(current["before"]) == _digest(snapshot["after"]):
            return "noop"
        if _digest(current["before"]) != _digest(snapshot["before"]):
            raise ValueError("G4 state changed since reviewed snapshot")
        _write_rows(db, current["after"])
        db.flush()
        if _digest(preview(db, root, lock=True)["before"]) != _digest(snapshot["after"]):
            raise ValueError("G4 post-write mismatch")
    return "applied"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-env", required=True)
    parser.add_argument("--apply-snapshot", type=Path)
    args = parser.parse_args(argv)
    url = os.environ.get(args.database_url_env)
    if not url:
        parser.error("explicit database URL environment variable is missing")
    from sqlalchemy import create_engine
    engine = None
    try:
        engine = create_engine(url)
        if engine.dialect.name != "postgresql":
            raise ValueError("G4 CLI requires explicit PostgreSQL target")
        if args.apply_snapshot:
            snapshot = json.loads(args.apply_snapshot.read_text(encoding="utf-8"))
            with Session(engine) as db:
                result = {"status": apply_snapshot(db, snapshot)}
        else:
            with engine.connect() as connection:
                connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                connection.exec_driver_sql("SET LOCAL statement_timeout = '5s'")
                with Session(bind=connection) as db:
                    result = preview(db)
                connection.rollback()
        print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
