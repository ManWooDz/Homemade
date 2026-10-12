"""Offline snapshot baseline. Gold is scoring-only; output is aggregate-only."""
from collections import Counter
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
import builtins
import argparse
import hashlib
import importlib
import importlib.metadata
import importlib.machinery
import importlib.util
import io
import inspect
import json
import math
from pathlib import Path
import platform
import socket
import sqlite3
import subprocess
import sys
import tempfile
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
COLLECTION = ROOT / "docs/nutrition-heldout/2026-10-07"
LABEL_HASH = "fa6fea585edd5c680cd2d56219dc4b2dfe85dbfe42a4efe63def9b0d2cc48786"
AUDIT_HASH = "35f08e260474d7ce074511c147f5cc1a2c4cb94ffedc5c436871ddf59e602a8c"
MACROS = ("calories", "protein_g", "carbs_g", "fat_g")
AXES = ("name_parsing", "row_identity", "quantity_resolution", "macro_completeness", "proxy_free_grounded_coverage")
MASS_UNITS = {"กรัม", "ก.", "กิโลกรัม", "กก.", "ขีด", "มิลลิกรัม", "มก."}
APPROVED_FINDINGS = {"reviewer_metadata_missing": 1, "review_time_metadata_missing_or_invalid": 1,
                     "standard_portion_convention_needs_explicit_acceptance": 10}
# Seal the receipts that link the already frozen corpus, not new annotations.
COLLECTION_RECEIPTS = {
    "review-01/freeze-verification.json": "4e819e5d3e9e1963c070717df60d9da3d0d531cf948a1c27c7f5aa6094668597",
    "review-01/collection-verification.json": "541e704d9759deac556078ba90a0bfcf5b361336c2f3046f7d3a7d90185283c3",
    "review-01/assistance-verification.json": "d38b24c05b34e7796ef6906d3a33bf04973b4ce809e316c896a51388086591b5",
    "review-01/output-overlap.json": "98ab2641d0ef29cc7ac98ef10649e9305e79017f670e97889bb4e3a6e96f7506",
    "live-run-01/metadata.json": "4023610cd91f0eb8f75a542890f2d92f4a7108d373eeebd23ecd098be84145ed",
    "live-run-01/manifest.json": "d17bf36bccf0ea446eff8aa7f5f24e172e80826ef57c3fbfe8e3c4ac87af0b7f",
}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def reject(_):
        raise ValueError("nonfinite_json")
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=reject)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def same_number(a, b, tolerance=1e-8):
    return number(a) and number(b) and math.isclose(a, b, rel_tol=0, abs_tol=tolerance)


def family(value):
    return {"INMU": "INMU", "INMU Thai FCD v3 August 2025": "INMU",
            "USDA": "USDA", "USDA FoodData Central": "USDA"}.get(value)


def identity(source):
    return family(source.get("source")), str(source.get("source_ref", "")).rsplit(":", 1)[-1], source.get("unit_basis")


def scoped(path, parent):
    path = Path(path).resolve()
    require(path.is_relative_to(parent.resolve()), "artifact_outside_scope")
    return path


def verify_hashes(hashes, parent):
    require(all(digest(scoped(parent / name, parent)) == value for name, value in hashes.items()), "artifact_hash_or_source_drift")


def verify_portion_records(rows, usda_records):
    records = {str(item["record"]["fdcId"]): item["record"] for item in usda_records}
    for row in rows:
        if row["annotation"]["gram_conversion_method"] != "ingredient_specific_portion":
            continue
        portions = [e for e in row["annotation"]["gram_conversion_evidence"] if isinstance(e.get("portion"), dict)]
        require(bool(portions), "portion_evidence_missing")
        for evidence in portions:
            ref = str(evidence.get("source_ref", "")).rsplit(":", 1)[-1]
            require(family(evidence.get("source")) == "USDA" and ref in records
                    and evidence["portion"] in records[ref].get("foodPortions", []), "portion_not_in_its_cited_record")


@contextmanager
def offline_guards():
    attempts = []
    def deny(code):
        def blocked(*args, **kwargs):
            attempts.append(code)
            raise RuntimeError(code)
        return blocked
    original_open, original_io_open = builtins.open, io.open
    original_import, original_import_module = builtins.__import__, importlib.import_module
    forbidden = {"main", "database.db", "nutrition.seed_inmu", "nutrition.seed_usda", "nutrition.llm_fallback"}
    def guarded_import(name, *args, **kwargs):
        fromlist = kwargs.get("fromlist", args[2] if len(args) > 2 else ()) or ()
        if name in forbidden or any(f"{name}.{member}" in forbidden for member in fromlist):
            return deny("live_module_import")(name)
        return original_import(name, *args, **kwargs)
    def guarded_import_module(name, package=None):
        if name in forbidden:
            return deny("live_module_import")(name)
        return original_import_module(name, package)
    def guarded_open(original):
        def opened(file, *args, **kwargs):
            if isinstance(file, (str, bytes, Path)) and Path(file.decode() if isinstance(file, bytes) else file).name.lower().startswith(".env"):
                return deny("environment_file_access")(file)
            return original(file, *args, **kwargs)
        return opened
    original_sqlite = sqlite3.dbapi2.connect
    def memory_connect(database, *args, **kwargs):
        if database != ":memory:" or kwargs.get("uri"):
            return deny("persistent_sqlite_access")(database)
        return original_sqlite(database, *args, **kwargs)
    with ExitStack() as stack:
        for owner, name in ((socket.socket, "connect"), (socket.socket, "connect_ex"),
                            (socket, "create_connection"), (socket, "getaddrinfo")):
            stack.enter_context(patch.object(owner, name, deny("network_access")))
        stack.enter_context(patch.object(builtins, "open", guarded_open(original_open)))
        stack.enter_context(patch.object(io, "open", guarded_open(original_io_open)))
        stack.enter_context(patch.object(builtins, "__import__", guarded_import))
        stack.enter_context(patch.object(importlib, "import_module", guarded_import_module))
        stack.enter_context(patch.object(sqlite3, "connect", memory_connect))
        stack.enter_context(patch.object(sqlite3.dbapi2, "connect", memory_connect))
        from sqlalchemy.engine import Engine
        original_connect = Engine.connect
        def guarded_engine(engine, *args, **kwargs):
            if engine.url.drivername != "sqlite" or engine.url.database != ":memory:":
                return deny("persistent_database_access")(engine)
            return original_connect(engine, *args, **kwargs)
        stack.enter_context(patch.object(Engine, "connect", guarded_engine))
        try:
            yield attempts
        finally:
            require(not attempts, "offline_guard_attempt_detected")


def validate_snapshot(snapshot):
    require(snapshot.get("schema_version") == 1 and snapshot.get("mode") == "read_only_nutrition_snapshot", "snapshot_schema")
    require(snapshot.get("transaction") == {"read_only": "on", "isolation": "repeatable read", "database": "homemade"}, "snapshot_transaction")
    tables = snapshot["tables"]
    require(set(tables) == {"ingredient_nutrition", "ingredient_nutrition_aliases"}, "snapshot_tables")
    require(snapshot["tables_sha256"] == hashlib.sha256(canonical(tables)).hexdigest(), "snapshot_tables_hash")
    require(snapshot["counts"] == {key: len(rows) for key, rows in tables.items()}, "snapshot_counts")
    nutrition_keys = set("id ingredient_name unit_basis calories protein_g carbs_g fat_g source source_ref portion_grams derivation created_at".split())
    alias_keys = {"id", "alias", "ingredient_nutrition_id"}
    foods, aliases = tables["ingredient_nutrition"], tables["ingredient_nutrition_aliases"]
    require(all(set(row) == nutrition_keys for row in foods) and all(set(row) == alias_keys for row in aliases), "snapshot_row_keys")
    require(all(type(row["id"]) is int and row["id"] > 0 for row in foods + aliases), "snapshot_ids")
    food_ids = {row["id"] for row in foods}
    require(len(food_ids) == len(foods) and len({row["id"] for row in aliases}) == len(aliases), "duplicate_snapshot_ids")
    require(len({row["alias"] for row in aliases}) == len(aliases), "duplicate_snapshot_aliases")
    require(all(type(row["ingredient_nutrition_id"]) is int and row["ingredient_nutrition_id"] in food_ids for row in aliases), "dangling_snapshot_alias")
    require(all(isinstance(row["ingredient_name"], str) and row["ingredient_name"] for row in foods), "snapshot_names")
    require(len({row["ingredient_name"] for row in foods}) == len(foods), "duplicate_snapshot_names")
    require(all(isinstance(row["alias"], str) and row["alias"] for row in aliases), "snapshot_aliases")
    for row in foods:
        require(all(isinstance(row[key], str) and row[key] for key in ("source", "source_ref", "unit_basis", "created_at")), "snapshot_source_fields")
        datetime.fromisoformat(row["created_at"])
        require(all(row[key] is None or number(row[key]) for key in MACROS), "snapshot_macro_number")
        require(row["derivation"] is None or isinstance(row["derivation"], dict), "snapshot_derivation")
        portions = row["portion_grams"]
        require(portions is None or (isinstance(portions, dict) and all(isinstance(k, str) and number(v) and v > 0 for k, v in portions.items())), "snapshot_portions")


def validate_freeze(labels, proof, expected_hash):
    require(expected_hash == proof.get("labels_sha256"), "freeze_proof_hash")
    require(labels.get("schema_version") == 1 and labels.get("frozen") is True
            and labels.get("mode") == "independent_human_reviewed_labels_frozen", "label_freeze_metadata")
    require(isinstance(labels.get("reviewer"), str) and labels["reviewer"].strip(), "reviewer_missing")
    stamp = datetime.fromisoformat(labels["reviewed_at_utc"])
    require(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0, "review_time_not_utc")
    require(proof.get("reviewer") == labels["reviewer"] and proof.get("reviewed_at_utc") == labels["reviewed_at_utc"], "review_metadata_conflict")
    require(proof.get("labels_frozen") is True and proof.get("freeze_ready") is True
            and proof.get("checks") and all(value is True for value in proof["checks"].values()), "freeze_proof_not_passed")
    provenance = labels["freeze_provenance"]
    require(provenance.get("label_version") == "nutrition-labels-v1", "label_version")
    conventions = provenance["accepted_conventions"]
    rows = labels["rows"]
    require(len(rows) == 55 and len({r["row_id"] for r in rows}) == 55, "label_row_ids")
    portion_ids = {r["row_id"] for r in rows if r["annotation"]["gram_conversion_method"] == "ingredient_specific_portion"}
    require(conventions.get("standard_measuring_spoon_and_generic_source_identity") is True
            and len(conventions["row_ids"]) == 10 and set(conventions["row_ids"]) == portion_ids, "convention_acceptance_missing")


def load_bundle(*, candidate=False):
    verify_hashes(COLLECTION_RECEIPTS, COLLECTION)
    review = COLLECTION / "review-01"
    path = review / "nutrition-labels-v1.frozen.json"
    require(digest(path) == LABEL_HASH, "label_byte_hash")
    require(path.with_suffix(".sha256").read_text(encoding="ascii") == f"{LABEL_HASH}  {path.name}\n", "label_sidecar")
    labels, proof = read(path), read(review / "freeze-verification.json")
    validate_freeze(labels, proof, LABEL_HASH)
    draft_path = review / "review-draft.json"
    draft = read(draft_path)
    require(digest(draft_path) == proof["draft_sha256"] == labels["freeze_provenance"]["draft_sha256"], "precursor_hash")
    require(set(labels) == set(draft) | {"freeze_provenance"}, "label_top_keys")
    require(all(labels[key] == value for key, value in draft.items() if key not in {"mode", "reviewer", "reviewed_at_utc", "frozen"}), "label_annotation_mutation")
    audit_path = COLLECTION / "audit_review.py"
    require(digest(audit_path) == AUDIT_HASH, "audit_code_hash")
    spec = importlib.util.spec_from_file_location("nutrition_heldout_audit_support", audit_path)
    support = importlib.util.module_from_spec(spec)
    exec(compile(audit_path.read_bytes(), str(audit_path), "exec", dont_inherit=True), support.__dict__)
    require(not any(support.annotation_issues(row["annotation"]) for row in labels["rows"]), "label_annotation_schema")
    provenance = labels["freeze_provenance"]
    previous_audit = scoped(COLLECTION / provenance["audit_path"], COLLECTION)
    require(digest(previous_audit) == provenance["audit_sha256"] == proof["fresh_audit_sha256"], "freeze_audit_hash")
    require(read(previous_audit)["audit_sha256"] == AUDIT_HASH, "freeze_audit_code")
    metadata_path = COLLECTION / labels["run"] / "metadata.json"
    metadata = read(metadata_path)
    sources = metadata["source_sha256"]
    require(len(sources) == 23, "collection_source_count")
    if not candidate:
        verify_hashes(sources, ROOT)
    verify_hashes(labels["raw_artifact_sha256"], COLLECTION / labels["run"])
    assistance = read(review / "assistance-verification.json")
    verify_hashes(assistance["artifact_sha256"], review)
    verify_hashes(assistance["source_archives"], review / "source-evidence")
    verify_portion_records(labels["rows"], read(review / "source-evidence/usda-records.json")["records"])
    snapshot_path = scoped(COLLECTION / metadata["snapshot"]["path"], COLLECTION)
    require(digest(snapshot_path) == metadata["snapshot"]["snapshot_sha256"], "snapshot_byte_hash")
    snapshot = read(snapshot_path)
    validate_snapshot(snapshot)
    require(snapshot["counts"] == {"ingredient_nutrition": 1052, "ingredient_nutrition_aliases": 2040}
            and snapshot["source_sha256"] == sources and snapshot["manifest_sha256"] == labels["manifest_sha256"], "snapshot_collection_link")
    overlap_path = review / "output-overlap.json"
    overlap = read(overlap_path)
    require(overlap["current_rows_retained"] == 55 and overlap["rows_excluded_or_replaced"] == 0, "overlap_denominator")
    verify_hashes(overlap["source_sha256"], ROOT)
    ids = {row["row_id"] for row in labels["rows"]}
    for field in ("rows_overlapping_historical_adjusted_ingredients", "rows_overlapping_historical_nutrition_fixture"):
        require(len(set(overlap[field])) == len(overlap[field]) and set(overlap[field]) <= ids, "overlap_ids")
    paths = {path, path.with_suffix(".sha256"), review / "freeze-verification.json", draft_path,
             audit_path, previous_audit, metadata_path, snapshot_path, overlap_path}
    paths.update(COLLECTION / name for name in COLLECTION_RECEIPTS)
    if not candidate:
        paths.update(scoped(ROOT / name, ROOT) for name in sources)
    paths.update(scoped(ROOT / name, ROOT) for name in overlap["source_sha256"])
    paths.update(COLLECTION / labels["run"] / name for name in labels["raw_artifact_sha256"])
    paths.update(p for p in (review / "source-evidence").iterdir() if p.is_file())
    hashes = {str(scoped(p, ROOT).relative_to(ROOT)): digest(p) for p in paths}
    fresh = support.audit()
    require(all(fresh["checks"].values()) and len(fresh["checks"]) == 16
            and fresh["finding_counts"] == APPROVED_FINDINGS and fresh["self_checks_passed"] == 12, "fresh_evidence_audit_failed")
    verify_hashes(hashes, ROOT)
    verify_hashes(COLLECTION_RECEIPTS, COLLECTION)
    require(digest(audit_path) == AUDIT_HASH and digest(snapshot_path) == metadata["snapshot"]["snapshot_sha256"], "bundle_read_drift")
    verify_hashes(labels["raw_artifact_sha256"], COLLECTION / labels["run"])
    verify_hashes(assistance["artifact_sha256"], review)
    verify_hashes(assistance["source_archives"], review / "source-evidence")
    verify_hashes(overlap["source_sha256"], ROOT)
    if not candidate:
        verify_hashes(sources, ROOT)
    return labels, snapshot, overlap, hashes, fresh["report"]


def candidate_code_hashes():
    paths = {Path(__file__), ROOT / "backend/tests/test_nutrition_heldout.py",
             ROOT / "backend/database/models.py"}
    paths.update((ROOT / "backend/nutrition").rglob("*.py"))
    init = ROOT / "backend/database/__init__.py"
    if init.exists():
        paths.add(init)
    paths.update(COLLECTION / name for name in
                 ("collect.py", "live_collect.py", "check_collection_offline.py", "check_live_adapter.py"))
    return {str(scoped(p, ROOT).relative_to(ROOT)): digest(p) for p in sorted(paths)}


def current_snapshot_sources():
    # Same inventory as the unchanged capture helper, without importing it or a DB client.
    paths = {ROOT / "backend/main.py", ROOT / "backend/recipe_contracts.py",
             ROOT / "backend/eval/nutrition_coverage.py"}
    paths.update(p for p in (ROOT / "backend/nutrition").rglob("*")
                 if p.is_file() and "__pycache__" not in p.parts)
    for name in ("google.genai._api_client", "google.genai.models", "google.genai.types",
                 "httpx._client", "httpx._transports.default", "httpcore._backends.sync"):
        paths.add(Path(importlib.import_module(name).__file__))
    return {str(scoped(p, ROOT).relative_to(ROOT)): digest(p) for p in sorted(paths)}


def load_candidate_snapshot(path, expected_hash, original):
    require(isinstance(expected_hash, str) and len(expected_hash) == 64
            and all(c in "0123456789abcdef" for c in expected_hash), "candidate_hash_format")
    path = scoped(path, COLLECTION)
    require(path != scoped(COLLECTION / original["path"], COLLECTION)
            and expected_hash != original["snapshot_sha256"], "original_snapshot_not_candidate")
    require(digest(path) == expected_hash, "candidate_snapshot_byte_hash")
    snapshot = read(path)
    validate_snapshot(snapshot)
    stamp = datetime.fromisoformat(snapshot["at_utc"])
    require(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0, "candidate_snapshot_time")
    require(snapshot["source_sha256"] == current_snapshot_sources(), "candidate_snapshot_source_drift")
    verify_hashes(snapshot["source_sha256"], ROOT)
    require(digest(path) == expected_hash, "candidate_snapshot_read_drift")
    return snapshot, {str(path.relative_to(ROOT)): expected_hash, **snapshot["source_sha256"]}


def verify_loaded_candidate(code_hashes):
    for name, module in tuple(sys.modules.items()):
        if name not in {"nutrition", "database"} and not name.startswith(("nutrition.", "database.")):
            continue
        if getattr(module, "__file__", None):
            path = scoped(module.__file__, ROOT / "backend")
            expected = ROOT / "backend" / Path(*name.split("."))
            expected = expected / "__init__.py" if name in {"nutrition", "database"} else expected.with_suffix(".py")
            require(path == expected and str(path.relative_to(ROOT)) in code_hashes, "unbound_candidate_module")
        else:
            require(name == "database" and module.__path__ and all(Path(p).resolve() == ROOT / "backend/database"
                                              for p in module.__path__), "candidate_namespace_path")
    verify_hashes(code_hashes, ROOT)


@contextmanager
def candidate_imports(code_hashes):
    require(not any(name in {"nutrition", "database"} or name.startswith(("nutrition.", "database."))
                    for name in sys.modules), "candidate_modules_already_loaded")
    verify_hashes(code_hashes, ROOT)
    compiled = compile(Path(__file__).read_bytes(), str(Path(__file__).resolve()), "exec", dont_inherit=True)
    functions = {c.co_name: c for c in compiled.co_consts if isinstance(c, types.CodeType)}
    require(all(inspect.unwrap(value).__code__ == functions[name] for name, value in globals().items()
                if isinstance(value, types.FunctionType) and value.__module__ == __name__), "loaded_evaluator_code_drift")
    original = importlib.machinery.SourceFileLoader.get_code
    def source_code(loader, fullname):
        if fullname in {"nutrition", "database"} or fullname.startswith(("nutrition.", "database.")):
            path = scoped(loader.path, ROOT / "backend")
            expected = ROOT / "backend" / Path(*fullname.split("."))
            expected = expected / "__init__.py" if fullname in {"nutrition", "database"} else expected.with_suffix(".py")
            relative = str(path.relative_to(ROOT))
            require(path == expected and relative in code_hashes and digest(path) == code_hashes[relative], "candidate_import_source_drift")
            return compile(path.read_bytes(), str(path), "exec", dont_inherit=True)
        return original(loader, fullname)
    with patch.object(importlib.machinery.SourceFileLoader, "get_code", source_code):
        yield
        verify_loaded_candidate(code_hashes)


def candidate_runtime():
    return {"python": sys.version, "platform": platform.platform(),
            "packages": {name: importlib.metadata.version(name) for name in
                         ("SQLAlchemy", "pgvector", "psycopg", "httpx", "google-genai", "pydantic", "python-dotenv")},
            "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "git_status": subprocess.check_output(["git", "status", "--short", "--", "backend/nutrition",
                         "backend/database", "backend/eval/nutrition_heldout.py", "backend/tests/test_nutrition_heldout.py"],
                         cwd=ROOT, text=True).splitlines()}


@contextmanager
def snapshot_session(snapshot):
    validate_snapshot(snapshot)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from database.models import Base, IngredientNutrition, IngredientNutritionAlias
    engine = create_engine("sqlite:///:memory:")
    try:
        Base.metadata.create_all(engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        with Session(engine) as db:
            for row in snapshot["tables"]["ingredient_nutrition"]:
                values = dict(row)
                values["created_at"] = datetime.fromisoformat(values["created_at"])
                db.add(IngredientNutrition(**values))
            db.flush()
            db.add_all(IngredientNutritionAlias(**row) for row in snapshot["tables"]["ingredient_nutrition_aliases"])
            db.flush()
            yield db
            db.rollback()
    finally:
        engine.dispose()


def observe(db, raw):
    from nutrition.parser import parse_ingredient_string
    from nutrition.lookup import match_ingredient
    from nutrition.units import resolve_grams, GLOBAL_UNIT_GRAMS
    from database.models import IngredientNutrition
    parsed = parse_ingredient_string(raw)
    match = match_ingredient(db, parsed.name)
    portions = match.portion_grams if match else None
    grams = resolve_grams(parsed.quantity, parsed.unit, portions)
    branch = "unresolved"
    if parsed.quantity is not None and parsed.unit is not None:
        if portions and parsed.unit in portions:
            branch = "ingredient_specific_portion"
        elif parsed.unit in GLOBAL_UNIT_GRAMS:
            branch = "direct_mass" if parsed.unit in MASS_UNITS else "approximate"
    result = {"parse_status": parsed.parse_status, "quantity": parsed.quantity, "unit": parsed.unit,
              "grams": grams, "conversion_method": branch, "match": None}
    if match:
        row = db.get(IngredientNutrition, match.ingredient_nutrition_id)
        result["match"] = {"source": match.source, "source_ref": match.source_ref, "unit_basis": row.unit_basis,
                           "macros": {key: getattr(match.macros, key) for key in MACROS},
                           "derivation": match.derivation, "portion_grams": portions}
    return result


def state(value, reason):
    return value, reason


def joint(states):
    return "fail" if "fail" in states else "unknown" if "unknown" in states else "pass"


def score(annotation, observed, convention_accepted=False):
    a, match = annotation, observed["match"]
    accepted = a["accepted_source_rows"]
    if a["source_availability"] == "absent":
        row = state("pass" if match is None else "fail", "verified_absent_abstention")
    elif a["source_availability"] == "present" and accepted:
        row = state("pass" if match and identity(match) in {identity(s) for s in accepted} else "fail", "accepted_row_comparison")
    else:
        row = state("unknown", "independent_row_identity_unresolved")
    if not number(a["grams"]):
        numeric_quantity = state("unknown", "independent_grams_unresolved")
    else:
        numeric_quantity = state("pass" if same_number(observed["grams"], a["grams"], .01) else "fail", "gram_value_comparison")
    method = observed["conversion_method"]
    if method == "approximate":
        qualification = state("fail", "runtime_water_density_approximation")
    elif method == "direct_mass" and a["gram_conversion_method"] == "direct_mass" and a["gram_conversion_source_backed"] is True:
        qualification = state("pass", "direct_mass")
    elif method == "ingredient_specific_portion":
        evidence = a["gram_conversion_evidence"]
        linked = match and any(identity(e) in {identity(s) for s in accepted} and family(e.get("source")) == family(match["source"])
                              and str(e.get("source_ref", "")).rsplit(":", 1)[-1] == str(match["source_ref"])
                              for e in evidence)
        portion_ok = (linked and a["gram_conversion_source_backed"] is True and convention_accepted
                      and a["gram_conversion_method"] == "ingredient_specific_portion"
                      and same_number(observed["quantity"], a["quantity_value"])
                      and observed["unit"] == a["quantity_unit"])
        qualification = state("pass" if portion_ok else "unknown", "portion_evidence_qualification")
    else:
        qualification = state("unknown", "conversion_evidence_unresolved")
    quantity = state(joint([numeric_quantity[0], qualification[0]]),
                     numeric_quantity[1] if numeric_quantity[0] != "pass" else qualification[1])
    derivation = (match or {}).get("derivation") or {}
    if not match:
        macro = state("fail" if a["source_availability"] == "present" and accepted else "unknown", "no_matched_macros")
    elif any(not number(match["macros"].get(key)) for key in MACROS):
        macro = state("fail", "runtime_macros_incomplete")
    elif derivation.get("energy_kcal") or derivation.get("calories") or derivation.get("carbs_g"):
        macro = state("fail", "project_imputed_macros")
    elif any(a["macro_provenance"][key] in {"missing", "project_imputed"} for key in MACROS):
        macro = state("fail", "independent_macros_not_complete_published")
    elif row[0] != "pass" or not accepted or a["source_availability"] != "present":
        macro = state("fail" if row[0] == "fail" else "unknown", "macro_row_identity_not_verified")
    elif any(a["macro_provenance"][key] != "source_published" or not number(a["published_macros"][key]) for key in MACROS) or not a["macro_evidence"]:
        macro = state("unknown", "macro_source_provenance_unresolved")
    elif match["unit_basis"] != a["macro_basis"] or any(not same_number(match["macros"][key], a["published_macros"][key]) for key in MACROS):
        macro = state("fail", "macro_source_value_or_basis_mismatch")
    else:
        macro = state("pass", "complete_source_published_macros")
    if derivation.get("proxy") or a["proxy_status"] == "proxy":
        proxy = state("fail", "known_proxy")
    elif row[0] == "pass" and match and a["proxy_status"] == "exact" and any(identity(s) == identity(match) and s["identity_relation"] == "exact" for s in accepted):
        proxy = state("pass", "independent_exact_identity")
    else:
        proxy = state("unknown", "proxy_identity_unverified")
    grounded = joint([row[0], quantity[0], macro[0], proxy[0]])
    if a["source_availability"] == "absent":
        grounded = "fail"
    return {"name_parsing": state("unknown", "missing_independent_parser_name_gold"), "row_identity": row,
            "quantity_resolution": quantity, "macro_completeness": macro,
            "proxy_free_grounded_coverage": state(grounded, "four_condition_conjunction"),
            "numeric_quantity_correctness": numeric_quantity, "conversion_qualification": qualification,
            "proxy_free_identity": proxy}


def summarize(states):
    counts = Counter(value for value, _ in states)
    require(set(counts) <= {"pass", "fail", "unknown"}, "invalid_axis_state")
    evaluable = counts["pass"] + counts["fail"]
    return {"total": len(states), **{key: counts[key] for key in ("pass", "fail", "unknown")},
            "evaluable": evaluable, "rate_on_evaluable": counts["pass"] / evaluable if evaluable else None,
            "unknown_reasons": dict(Counter(reason for value, reason in states if value == "unknown"))}


def evaluate(db, labels, overlap):
    conventions = set(labels["freeze_provenance"]["accepted_conventions"]["row_ids"])
    observations, results = [], []
    for row in labels["rows"]:
        observed = observe(db, row["raw_ingredient"])
        observations.append(observed)
        results.append(score(row["annotation"], observed, row["row_id"] in conventions))
    axes = {key: summarize([r[key] for r in results]) for key in AXES}
    coverage = axes["proxy_free_grounded_coverage"]
    coverage.update(verified_grounded_count=coverage["pass"], all_rows_denominator=len(results),
                    verified_grounded_fraction_all_rows=coverage["pass"] / len(results) if results else None)
    strata_ids = {"convention_dependent": conventions,
                  "not_convention_dependent": {r["row_id"] for r in labels["rows"]} - conventions,
                  "historical_adjusted_string_overlap": set(overlap["rows_overlapping_historical_adjusted_ingredients"]),
                  "historical_nutrition_fixture_string_overlap": set(overlap["rows_overlapping_historical_nutrition_fixture"])}
    strata = {name: {key: summarize([result[key] for row, result in zip(labels["rows"], results) if row["row_id"] in ids])
                     for key in AXES} for name, ids in strata_ids.items()}
    diagnostics = {"parse_status_counts": dict(Counter(o["parse_status"] for o in observations)),
                   "numeric_gram_available_count": sum(number(o["grams"]) for o in observations),
                   "match_available_count": sum(o["match"] is not None for o in observations),
                   "numeric_four_macros_available_count": sum(o["match"] is not None and all(number(o["match"]["macros"][k]) for k in MACROS) for o in observations),
                   "numeric_quantity_correctness": summarize([r["numeric_quantity_correctness"] for r in results]),
                   "conversion_qualification": summarize([r["conversion_qualification"] for r in results]),
                   "proxy_free_identity": summarize([r["proxy_free_identity"] for r in results]),
                   "row_identity_expected_present": summarize([r["row_identity"] for row, r in zip(labels["rows"], results) if row["annotation"]["source_availability"] == "present"]),
                   "verified_absent_abstention": summarize([r["row_identity"] for row, r in zip(labels["rows"], results) if row["annotation"]["source_availability"] == "absent"])}
    return axes, diagnostics, strata


def run(candidate_snapshot=None, candidate_snapshot_sha256=None):
    sys.dont_write_bytecode = True
    candidate = candidate_snapshot is not None or candidate_snapshot_sha256 is not None
    directory = Path(tempfile.mkdtemp(prefix="candidate-" if candidate else "baseline-", dir=COLLECTION))
    try:
        require(not any(name in sys.modules for name in ("main", "database.db")), "live_modules_already_loaded")
        require(not candidate or (candidate_snapshot is not None and candidate_snapshot_sha256 is not None), "candidate_inputs_paired")
        with offline_guards() as attempts:
            code_hashes = candidate_code_hashes() if candidate else None
            runtime = candidate_runtime() if candidate else None
            labels, snapshot, overlap, hashes, fresh_audit = load_bundle(candidate=candidate)
            code_paths = [ROOT / "backend/eval/nutrition_heldout.py", ROOT / "backend/tests/test_nutrition_heldout.py", ROOT / "backend/database/models.py"]
            snapshot_hashes = {}
            declared_sources = None
            if candidate:
                metadata = read(COLLECTION / labels["run"] / "metadata.json")
                declared_sources = metadata["source_sha256"]
                snapshot, snapshot_hashes = load_candidate_snapshot(candidate_snapshot, candidate_snapshot_sha256, metadata["snapshot"])
            else:
                code_hashes = {str(p.relative_to(ROOT)): digest(p) for p in code_paths}
            with ExitStack() as stack:
                if candidate:
                    stack.enter_context(candidate_imports(code_hashes))
                db = stack.enter_context(snapshot_session(snapshot))
                axes, diagnostics, strata = evaluate(db, labels, overlap)
            verify_hashes(hashes, ROOT)
            verify_hashes(code_hashes, ROOT)
            verify_hashes(snapshot_hashes, ROOT)
            if candidate:
                require(snapshot["source_sha256"] == current_snapshot_sources(), "candidate_source_inventory_drift")
                require(code_hashes == candidate_code_hashes() and runtime == candidate_runtime(), "candidate_runtime_drift")
            require(not attempts, "offline_guard_attempt_detected")
            report = {"schema_version": 1, "evaluation_policy_version": "nutrition-heldout-five-axis-v1",
                      "mode": "offline_snapshot_five_axis_baseline", "at_utc": datetime.now(timezone.utc).isoformat(),
                      "label_version": "nutrition-labels-v1", "reviewer": labels["reviewer"], "reviewed_at_utc": labels["reviewed_at_utc"],
                      "artifact_sha256": hashes, "code_sha256": code_hashes, "fresh_evidence_audit": fresh_audit,
                      "total_rows": len(labels["rows"]), "label_status_counts": dict(Counter(r["annotation"]["status"] for r in labels["rows"])),
                      "axes": axes, "operational_diagnostics": diagnostics, "strata": strata,
                      "servings_mismatch_count": sum(r["servings_mismatch"] for r in labels["recipes"]),
                      "guard_attempts": len(attempts), "input_unchanged": True,
                      "limits": ["name accuracy unavailable: v1 lacks independent parser-name gold",
                                 "45 unresolved retained; evaluable denominators differ by axis",
                                 "source-specific spoon/generic identity conventions accepted, not observed physical quantities",
                                 "overlap strata overlap; new recipes are not ingredient-disjoint generalization",
                                 "cached evidence and point-in-time snapshot, not live DB or clinical validation",
                                 "runtime zero-constants/LLM fallback/calculator flags not exercised; parser/lookup/units observation only",
                                 "no threshold, runtime tuning, provider/DB/network calls or row-level gold output"]}
            if candidate:
                report.pop("artifact_sha256")
                report.pop("code_sha256")
                report.update(schema_version=2, mode="offline_candidate_snapshot_five_axis",
                              run_version="nutrition-candidate-run-v1", collection_artifact_sha256=hashes,
                              declared_collection_source_sha256=declared_sources, historical_source_replay_verified=False,
                              candidate_code_sha256=code_hashes, candidate_snapshot_sha256=candidate_snapshot_sha256,
                              candidate_snapshot_path=str(Path(candidate_snapshot).resolve().relative_to(ROOT)),
                              candidate_snapshot_tables_sha256=snapshot["tables_sha256"], candidate_snapshot_counts=snapshot["counts"],
                              candidate_snapshot_at_utc=snapshot["at_utc"], candidate_snapshot_source_sha256=snapshot["source_sha256"],
                              runtime=runtime)
                report["limits"].append("historical collection source hashes are declared provenance; complete old source-tree replay is unverified")
            target = directory / "report.json"
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write("\n")
            require(read(target) == report, "report_readback")
        return {"report": str(target), "report_sha256": digest(target), "total_rows": report["total_rows"],
                "axes": axes, "guard_attempts": 0, "input_unchanged": True}
    except Exception as exc:
        stopped = {"mode": "stopped_NOT_candidate" if candidate else "stopped_NOT_baseline", "error_type": type(exc).__name__,
                   "reason": "integrity_or_execution_gate_failed", "no_score": True}
        with (directory / "stopped.json").open("x", encoding="utf-8") as stream:
            json.dump(stopped, stream)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-snapshot", type=Path)
    parser.add_argument("--candidate-snapshot-sha256")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.candidate_snapshot, args.candidate_snapshot_sha256)))
    except Exception as exc:
        print(json.dumps({"status": "stopped", "error_type": type(exc).__name__}))
        raise SystemExit(1) from None
