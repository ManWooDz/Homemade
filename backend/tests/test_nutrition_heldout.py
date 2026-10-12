"""Synthetic evaluator checks only: never load held-out annotations."""
from copy import deepcopy
from contextlib import ExitStack, nullcontext
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from eval import nutrition_heldout as heldout


def annotation():
    return {"status": "reviewed", "accepted_identity": "synthetic source identity", "source_availability": "present",
            "accepted_source_rows": [{"source": "USDA FoodData Central", "source_ref": "TEST", "unit_basis": "100g", "identity_relation": "exact"}],
            "grams": 20., "quantity_value": 20., "quantity_unit": "กรัม", "gram_conversion_method": "direct_mass",
            "gram_conversion_source_backed": True, "gram_conversion_evidence": [{}],
            "published_macros": {key: 0. for key in heldout.MACROS}, "macro_basis": "100g",
            "macro_provenance": {key: "source_published" for key in heldout.MACROS}, "macro_evidence": [{}],
            "proxy_status": "exact"}


def observation():
    return {"quantity": 20., "unit": "กรัม", "grams": 20., "parse_status": "ok", "conversion_method": "direct_mass",
            "match": {"source": "USDA", "source_ref": "TEST", "unit_basis": "100g", "derivation": None,
                      "macros": {key: 0. for key in heldout.MACROS}, "portion_grams": None}}


def snapshot():
    foods = [{"id": 1, "ingredient_name": "synthetic food", "source": "USDA", "source_ref": "TEST", "unit_basis": "100g",
              **{key: 0. for key in heldout.MACROS}, "portion_grams": {"ช้อนชา": 4.}, "derivation": None,
              "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()}]
    aliases = [{"id": 1, "alias": "synthetic food", "ingredient_nutrition_id": 1}]
    tables = {"ingredient_nutrition": foods, "ingredient_nutrition_aliases": aliases}
    return {"schema_version": 1, "mode": "read_only_nutrition_snapshot", "tables": tables,
            "tables_sha256": hashlib.sha256(heldout.canonical(tables)).hexdigest(),
            "counts": {key: len(rows) for key, rows in tables.items()},
            "transaction": {"read_only": "on", "isolation": "repeatable read", "database": "homemade"}}


def reseal(value):
    value["counts"] = {key: len(rows) for key, rows in value["tables"].items()}
    value["tables_sha256"] = hashlib.sha256(heldout.canonical(value["tables"])).hexdigest()
    return value


def synthetic_bundle(folder):
    """Seal a made-up 55-row collection; no private artifacts are loaded."""
    def save(name, value):
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return heldout.digest(path)
    sources = {f"source-{i}.py": save(f"source-{i}.py", i) for i in range(23)}
    original = snapshot()
    original.update(source_sha256=sources, manifest_sha256="synthetic")
    food = original["tables"]["ingredient_nutrition"][0]
    original["tables"]["ingredient_nutrition"] = [dict(food, id=i, ingredient_name=f"historical synthetic {i}") for i in range(1, 1053)]
    original["tables"]["ingredient_nutrition_aliases"] = [
        {"id": i, "alias": f"historical alias {i}", "ingredient_nutrition_id": 1} for i in range(1, 2041)]
    reseal(original)
    old_ref = {"path": "old/snapshot.json", "snapshot_sha256": save("old/snapshot.json", original)}
    portion = {"amount": 1, "gramWeight": 4}
    rows = []
    for i in range(55):
        a = annotation()
        if i < 10:
            a["gram_conversion_method"] = "ingredient_specific_portion"
            a["gram_conversion_evidence"] = [{"source": "USDA", "source_ref": "1", "portion": portion}]
        rows.append({"row_id": f"S{i}", "raw_ingredient": "synthetic food 20 กรัม", "annotation": a})
    conventions = {"standard_measuring_spoon_and_generic_source_identity": True, "row_ids": [f"S{i}" for i in range(10)]}
    draft = {"schema_version": 1, "frozen": False, "mode": "draft", "reviewer": None, "reviewed_at_utc": None,
             "run": "run", "manifest_sha256": "synthetic", "rows": rows, "recipes": [],
             "raw_artifact_sha256": {"raw.json": save("run/raw.json", {"synthetic": True})}}
    draft_hash = save("review-01/review-draft.json", draft)
    audit_path = folder / "audit_review.py"
    audit_path.write_text(
        'def annotation_issues(a): return []\n'
        'def audit():\n'
        ' return {"checks": {str(i): True for i in range(16)}, "finding_counts": '
        + repr(heldout.APPROVED_FINDINGS) + ', "self_checks_passed": 12, "report": "synthetic"}\n', encoding="utf-8")
    audit_hash = heldout.digest(audit_path)
    previous_hash = save("review-01/previous-audit.json", {"audit_sha256": audit_hash})
    labels = dict(draft, frozen=True, mode="independent_human_reviewed_labels_frozen", reviewer="synthetic reviewer",
                  reviewed_at_utc="2026-01-01T00:00:00Z", freeze_provenance={"label_version": "nutrition-labels-v1",
                  "draft_sha256": draft_hash, "audit_path": "review-01/previous-audit.json", "audit_sha256": previous_hash,
                  "accepted_conventions": conventions})
    label_hash = save("review-01/nutrition-labels-v1.frozen.json", labels)
    (folder / "review-01/nutrition-labels-v1.frozen.sha256").write_text(
        f"{label_hash}  nutrition-labels-v1.frozen.json\n", encoding="ascii")
    save("review-01/freeze-verification.json", {"labels_sha256": label_hash, "draft_sha256": draft_hash,
         "fresh_audit_sha256": previous_hash, "reviewer": labels["reviewer"], "reviewed_at_utc": labels["reviewed_at_utc"],
         "labels_frozen": True, "freeze_ready": True, "checks": {"synthetic": True}})
    evidence = {"source-evidence/usda-records.json": save("review-01/source-evidence/usda-records.json",
                {"records": [{"record": {"fdcId": 1, "foodPortions": [portion]}}]}),
                "source-evidence/inmu.html": save("review-01/source-evidence/inmu.html", "synthetic HTML")}
    archive_hash = save("review-01/source-evidence/archive.zip", "synthetic archive")
    save("review-01/assistance-verification.json", {"artifact_sha256": evidence, "source_archives": {"archive.zip": archive_hash}})
    save("review-01/collection-verification.json", {"synthetic": True})
    save("run/metadata.json", {"source_sha256": sources, "snapshot": old_ref})
    save("run/manifest.json", {"synthetic": True})
    save("review-01/output-overlap.json", {"current_rows_retained": 55, "rows_excluded_or_replaced": 0, "source_sha256": {},
         "rows_overlapping_historical_adjusted_ingredients": [], "rows_overlapping_historical_nutrition_fixture": []})
    receipts = {p: heldout.digest(folder / p) for p in ("review-01/freeze-verification.json", "review-01/assistance-verification.json",
                "review-01/collection-verification.json", "review-01/output-overlap.json", "run/metadata.json", "run/manifest.json")}
    return label_hash, audit_hash, receipts, old_ref


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="nutrition-candidate-test-"))
        label_hash, audit_hash, receipts, self.original = synthetic_bundle(self.folder)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        # Other discovered tests import live modules; isolate only this synthetic fixture.
        self.stack.enter_context(patch.dict(sys.modules))
        for name in ("main", "database.db"):
            sys.modules.pop(name, None)
        for key, value in (("ROOT", self.folder), ("COLLECTION", self.folder), ("LABEL_HASH", label_hash),
                           ("AUDIT_HASH", audit_hash), ("COLLECTION_RECEIPTS", receipts)):
            self.stack.enter_context(patch.object(heldout, key, value))

    def test_historical_drift_stops_but_candidate_keeps_declared_provenance(self):
        (self.folder / "source-0.py").write_text("changed current code", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "artifact_hash_or_source_drift"):
            heldout.load_bundle()
        labels, original, _, hashes, _ = heldout.load_bundle(candidate=True)
        self.assertEqual(len(labels["rows"]), 55)
        self.assertNotIn("source-0.py", hashes)
        self.assertNotEqual(original["source_sha256"]["source-0.py"], heldout.digest(self.folder / "source-0.py"))
        heldout.verify_hashes(hashes, self.folder)

    def test_frozen_inputs_tamper_stops_both_modes(self):
        for name in ("review-01/nutrition-labels-v1.frozen.json", "review-01/review-draft.json", "audit_review.py",
                     "review-01/previous-audit.json", "run/raw.json", "run/manifest.json", "run/metadata.json",
                     "review-01/source-evidence/archive.zip", "review-01/source-evidence/inmu.html",
                     "review-01/assistance-verification.json", "review-01/freeze-verification.json"):
            with self.subTest(name=name):
                path = self.folder / name
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                try:
                    for candidate in (False, True):
                        with self.assertRaises(ValueError):
                            heldout.load_bundle(candidate=candidate)
                finally:
                    path.write_bytes(original)

    def save_candidate(self, value=None):
        value = snapshot() if value is None else value
        source = self.folder / "candidate-code.py"
        source.write_text("synthetic current", encoding="utf-8")
        value.update(at_utc="2026-10-12T00:00:00Z", source_sha256={source.name: heldout.digest(source)})
        path = self.folder / "current/snapshot.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path, heldout.digest(path), value

    def test_explicit_new_snapshot_no_historical_count_and_source_drift(self):
        path, sha, value = self.save_candidate()
        with patch.object(heldout, "current_snapshot_sources", return_value=value["source_sha256"]):
            result, pins = heldout.load_candidate_snapshot(path, sha, self.original)
            self.assertEqual(result["counts"]["ingredient_nutrition_aliases"], 1)
            heldout.verify_hashes(pins, self.folder)
            (self.folder / "candidate-code.py").write_text("drift", encoding="utf-8")
            with self.assertRaises(ValueError):
                heldout.verify_hashes(pins, self.folder)
        with patch.object(heldout, "current_snapshot_sources", return_value={}):
            with self.assertRaisesRegex(ValueError, "candidate_snapshot_source_drift"):
                heldout.load_candidate_snapshot(path, sha, self.original)

    def test_bad_snapshot_byte_path_original_and_metadata_rejected(self):
        path, sha, value = self.save_candidate()
        with patch.object(heldout, "current_snapshot_sources", return_value=value["source_sha256"]):
            for target, expected in ((path, "0" * 64), (path, "malformed"), (path, sha.upper()),
                                     (self.folder / "../outside.json", sha),
                                     (self.folder / self.original["path"], self.original["snapshot_sha256"])):
                with self.subTest(target=str(target), expected=expected), self.assertRaises(ValueError):
                    heldout.load_candidate_snapshot(target, expected, self.original)
            for mutate in (lambda s: s.update(counts={}), lambda s: s.update(tables_sha256="wrong"),
                           lambda s: s.update(at_utc="2026-01-01T00:00:00"),
                           lambda s: s["transaction"].update(read_only="off"),
                           lambda s: s["tables"]["ingredient_nutrition"][0].update(carbs_g="missing")):
                bad = deepcopy(value)
                mutate(bad)
                path.write_text(json.dumps(bad), encoding="utf-8")
                with self.assertRaises(ValueError):
                    heldout.load_candidate_snapshot(path, heldout.digest(path), self.original)

    def test_inputs_must_be_paired_and_leave_stopped_not_score(self):
        for path, sha in ((self.folder / "missing", None), (None, "0" * 64)):
            with self.assertRaisesRegex(ValueError, "candidate_inputs_paired"), patch.object(heldout, "evaluate") as evaluate:
                heldout.run(path, sha)
            evaluate.assert_not_called()
        stopped = list(self.folder.glob("candidate-*/stopped.json"))
        self.assertEqual(len(stopped), 2)
        self.assertTrue(all(heldout.read(p)["no_score"] for p in stopped))
        self.assertFalse(list(self.folder.glob("candidate-*/report.json")))

    def test_preloaded_live_module_stops_run_before_scoring(self):
        with patch.dict(sys.modules, {"main": types.ModuleType("main")}), \
             patch.object(heldout, "evaluate") as evaluate, \
             self.assertRaisesRegex(ValueError, "live_modules_already_loaded"):
            heldout.run(self.folder / "missing", "0" * 64)
        evaluate.assert_not_called()
        self.assertFalse(list(self.folder.glob("candidate-*/report.json")))

    def test_preloaded_and_wrong_path_project_modules_rejected(self):
        fake = types.ModuleType("nutrition.parser")
        fake.__file__ = str(self.folder / "outside/parser.py")
        with patch.dict(sys.modules, {"nutrition.parser": fake}):
            with self.assertRaisesRegex(ValueError, "candidate_modules_already_loaded"):
                with heldout.candidate_imports({}):
                    self.fail("preloaded module executed")
            with self.assertRaises(ValueError):
                heldout.verify_loaded_candidate({})

    def test_independent_snapshot_changes_observation_without_gold_aliases(self):
        value = snapshot()
        before = deepcopy(value)
        with heldout.offline_guards(), heldout.snapshot_session(value) as db:
            first = heldout.observe(db, "synthetic food 20 กรัม")
        value["tables"]["ingredient_nutrition"][0]["calories"] = 12.
        with heldout.offline_guards(), heldout.snapshot_session(reseal(value)) as db:
            second = heldout.observe(db, "synthetic food 20 กรัม")
        self.assertEqual(first["match"]["macros"]["calories"], 0.)
        self.assertEqual(second["match"]["macros"]["calories"], 12.)
        self.assertEqual(value["tables"]["ingredient_nutrition_aliases"], before["tables"]["ingredient_nutrition_aliases"])

    def test_candidate_report_is_versioned_aggregate_only_and_inputs_unchanged(self):
        path, sha, value = self.save_candidate()
        before = {p: heldout.digest(p) for p in self.folder.rglob("*") if p.is_file()}
        with patch.object(heldout, "current_snapshot_sources", return_value=value["source_sha256"]), \
             patch.object(heldout, "candidate_code_hashes", return_value=value["source_sha256"]), \
             patch.object(heldout, "candidate_runtime", return_value={"python": "synthetic"}), \
             patch.object(heldout, "candidate_imports", return_value=nullcontext()):
            first = heldout.run(path, sha)
            second = heldout.run(path, sha)
        self.assertNotEqual(first["report"], second["report"])
        report = heldout.read(first["report"])
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["run_version"], "nutrition-candidate-run-v1")
        self.assertEqual(report["evaluation_policy_version"], "nutrition-heldout-five-axis-v1")
        self.assertFalse(report["historical_source_replay_verified"])
        self.assertEqual(report["candidate_snapshot_counts"]["ingredient_nutrition_aliases"], 1)
        self.assertEqual(report["total_rows"], 55)
        self.assertEqual(report["axes"]["name_parsing"]["unknown"], 55)
        self.assertNotIn("rows", report)
        self.assertNotIn("raw_ingredient", json.dumps(report))
        self.assertNotIn("artifact_sha256", report)
        self.assertTrue(all(heldout.digest(p) == expected for p, expected in before.items()))

    def test_candidate_code_drift_leaves_no_score(self):
        path, sha, value = self.save_candidate()
        actual_evaluate = heldout.evaluate
        def drift(*args):
            result = actual_evaluate(*args)
            (self.folder / "candidate-code.py").write_text("changed during evaluation", encoding="utf-8")
            return result
        with patch.object(heldout, "current_snapshot_sources", return_value=value["source_sha256"]), \
             patch.object(heldout, "candidate_code_hashes", return_value=value["source_sha256"]), \
             patch.object(heldout, "candidate_runtime", return_value={"python": "synthetic"}), \
             patch.object(heldout, "candidate_imports", return_value=nullcontext()), \
             patch.object(heldout, "evaluate", side_effect=drift):
            with self.assertRaisesRegex(ValueError, "artifact_hash_or_source_drift"):
                heldout.run(path, sha)
        self.assertFalse(list(self.folder.glob("candidate-*/report.json")))
        self.assertTrue(heldout.read(next(self.folder.glob("candidate-*/stopped.json")))["no_score"])

    def test_caught_guard_attempt_cannot_publish_a_score(self):
        path, sha, value = self.save_candidate()
        actual_evaluate = heldout.evaluate
        def caught(*args):
            try:
                socket.getaddrinfo("example.invalid", 443)
            except RuntimeError:
                pass
            return actual_evaluate(*args)
        with patch.object(heldout, "current_snapshot_sources", return_value=value["source_sha256"]), \
             patch.object(heldout, "candidate_code_hashes", return_value=value["source_sha256"]), \
             patch.object(heldout, "candidate_runtime", return_value={"python": "synthetic"}), \
             patch.object(heldout, "candidate_imports", return_value=nullcontext()), \
             patch.object(heldout, "evaluate", side_effect=caught):
            with self.assertRaisesRegex(ValueError, "offline_guard_attempt_detected"):
                heldout.run(path, sha)
        self.assertFalse(list(self.folder.glob("candidate-*/report.json")))


class CandidateRuntimeTests(unittest.TestCase):
    def test_fresh_process_imports_pinned_sources_not_cached_bytecode(self):
        folder = Path(tempfile.mkdtemp(prefix="nutrition-candidate-runtime-test-"))
        path = folder / "synthetic-snapshot.json"
        path.write_text(json.dumps(snapshot()), encoding="utf-8")
        program = '''
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
from eval import nutrition_heldout as h
paths = [Path(h.__file__), h.ROOT / "backend/database/models.py"]
paths += list((h.ROOT / "backend/nutrition").rglob("*.py"))
pins = {str(p.relative_to(h.ROOT)): h.digest(p) for p in paths}
with h.offline_guards(), h.candidate_imports(pins):
    with h.snapshot_session(h.read(sys.argv[2])) as db:
        assert h.observe(db, "synthetic food 20 กรัม")["match"] is not None
print("fresh_candidate_imports_passed")
'''
        result = subprocess.run([sys.executable, "-B", "-c", program, str(heldout.ROOT / "backend"), str(path)],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "fresh_candidate_imports_passed")


class ScoringTests(unittest.TestCase):
    def test_complete_published_zero_passes_without_name_accuracy(self):
        result = heldout.score(annotation(), observation())
        self.assertEqual(result["name_parsing"][0], "unknown")
        self.assertTrue(all(result[key][0] == "pass" for key in heldout.AXES[1:]))

    def test_wrong_source_ref_source_and_basis_fail_identity(self):
        for key, value in (("source_ref", "WRONG"), ("source", "INMU"), ("unit_basis", "100ml")):
            with self.subTest(key=key):
                observed = observation()
                observed["match"][key] = value
                self.assertEqual(heldout.score(annotation(), observed)["row_identity"][0], "fail")

    def test_unresolved_can_have_evaluable_mass_without_verified_identity(self):
        a = annotation()
        a.update(status="unresolved", source_availability="unknown", accepted_source_rows=[], proxy_status="unknown")
        result = heldout.score(a, observation())
        self.assertEqual(result["row_identity"][0], "unknown")
        self.assertEqual(result["quantity_resolution"][0], "pass")
        self.assertEqual(result["proxy_free_grounded_coverage"][0], "unknown")

    def test_absent_abstention_not_grounded(self):
        a, observed = annotation(), observation()
        a.update(source_availability="absent", accepted_source_rows=[])
        observed["match"] = None
        result = heldout.score(a, observed)
        self.assertEqual(result["row_identity"][0], "pass")
        self.assertEqual(result["proxy_free_grounded_coverage"][0], "fail")

    def test_unknown_is_not_wrong_and_no_proxy_field_is_not_exact(self):
        a = annotation()
        a.update(source_availability="unknown", accepted_source_rows=[], grams=None, proxy_status="unknown",
                 macro_provenance={key: "unknown" for key in heldout.MACROS})
        result = heldout.score(a, observation())
        self.assertTrue(all(result[key][0] == "unknown" for key in heldout.AXES))

    def test_known_proxy_failure_dominates_unknown(self):
        a = annotation()
        a.update(source_availability="unknown", accepted_source_rows=[], grams=None)
        observed = observation()
        observed["match"]["derivation"] = {"proxy": "synthetic substitute"}
        self.assertEqual(heldout.score(a, observed)["proxy_free_grounded_coverage"][0], "fail")

    def test_water_density_cannot_ground_even_if_numeric_equal(self):
        observed = observation()
        observed["conversion_method"] = "approximate"
        result = heldout.score(annotation(), observed)
        self.assertEqual(result["numeric_quantity_correctness"][0], "pass")
        self.assertEqual(result["quantity_resolution"][0], "fail")
        self.assertEqual(result["proxy_free_grounded_coverage"][0], "fail")

    def test_portion_requires_link_convention_and_correct_quantity(self):
        a, observed = annotation(), observation()
        a.update(quantity_value=2., quantity_unit="ช้อนชา", gram_conversion_method="ingredient_specific_portion")
        a["gram_conversion_evidence"] = [{"source": "USDA", "source_ref": "TEST", "unit_basis": "100g"}]
        observed.update(quantity=2., unit="ช้อนชา", conversion_method="ingredient_specific_portion")
        self.assertEqual(heldout.score(a, observed, True)["quantity_resolution"][0], "pass")
        self.assertEqual(heldout.score(a, observed, False)["quantity_resolution"][0], "unknown")
        a["gram_conversion_evidence"][0]["source_ref"] = "OTHER"
        self.assertEqual(heldout.score(a, observed, True)["quantity_resolution"][0], "unknown")

    def test_unknown_unit_and_quantity_tolerance_are_not_guessed(self):
        observed = observation()
        observed.update(grams=None, conversion_method="unresolved")
        self.assertEqual(heldout.score(annotation(), observed)["quantity_resolution"][0], "fail")
        self.assertFalse(heldout.same_number(1000000., 1000000.1, .01))
        self.assertTrue(heldout.same_number(20., 20.005, .01))

    def test_missing_runtime_and_source_macros_cannot_pass(self):
        for key in heldout.MACROS:
            with self.subTest(key=key):
                observed = observation()
                observed["match"]["macros"][key] = None
                self.assertEqual(heldout.score(annotation(), observed)["macro_completeness"][0], "fail")
                a = annotation()
                a["macro_provenance"][key] = "missing"
                a["published_macros"][key] = None
                self.assertEqual(heldout.score(a, observation())["macro_completeness"][0], "fail")

    def test_project_derivations_are_estimated_not_source_calculations(self):
        for derivation in ({"energy_kcal": "atwater"}, {"carbs_g": "by_difference"}, {"carbs_g": "by_difference_clamped"}):
            observed = observation()
            observed["match"]["derivation"] = derivation
            self.assertEqual(heldout.score(annotation(), observed)["macro_completeness"][0], "fail")
        self.assertEqual(heldout.score(annotation(), observation())["macro_completeness"][0], "pass")

    def test_wrong_published_value_basis_and_unknown_provenance(self):
        a = annotation()
        a["published_macros"]["carbs_g"] = 5.
        self.assertEqual(heldout.score(a, observation())["macro_completeness"][0], "fail")
        a = annotation()
        a["macro_basis"] = "100ml"
        self.assertEqual(heldout.score(a, observation())["macro_completeness"][0], "fail")
        a = annotation()
        a["macro_provenance"]["calories"] = "unknown"
        self.assertEqual(heldout.score(a, observation())["macro_completeness"][0], "unknown")

    def test_nonnumeric_boolean_negative_nonfinite_rejected(self):
        for value in (True, -1, float("nan"), float("inf"), "0"):
            self.assertFalse(heldout.number(value))
            observed = observation()
            observed["match"]["macros"]["protein_g"] = value
            self.assertEqual(heldout.score(annotation(), observed)["macro_completeness"][0], "fail")

    def test_empty_evaluable_rate_null_and_conjunction(self):
        self.assertIsNone(heldout.summarize([])["rate_on_evaluable"])
        self.assertIsNone(heldout.summarize([("unknown", "no_gold")])["rate_on_evaluable"])
        self.assertEqual(heldout.joint(["pass", "unknown"]), "unknown")
        self.assertEqual(heldout.joint(["fail", "unknown"]), "fail")

    def test_all_55_retained_and_overlapping_strata_not_added(self):
        rows = [{"row_id": f"S{i}", "raw_ingredient": "synthetic", "annotation": annotation()} for i in range(55)]
        labels = {"rows": rows, "freeze_provenance": {"accepted_conventions": {"row_ids": [f"S{i}" for i in range(10)]}}}
        overlap = {"rows_overlapping_historical_adjusted_ingredients": ["S0", "S1"], "rows_overlapping_historical_nutrition_fixture": ["S1"]}
        with patch.object(heldout, "observe", return_value=observation()):
            axes, diagnostics, strata = heldout.evaluate(None, labels, overlap)
        for value in axes.values():
            self.assertEqual(value["pass"] + value["fail"] + value["unknown"], 55)
        self.assertEqual(axes["name_parsing"]["unknown"], 55)
        self.assertEqual(strata["convention_dependent"]["row_identity"]["total"], 10)
        self.assertEqual(strata["not_convention_dependent"]["row_identity"]["total"], 45)
        self.assertEqual(strata["historical_nutrition_fixture_string_overlap"]["row_identity"]["total"], 1)


class BoundaryTests(unittest.TestCase):
    def test_portion_must_belong_to_cited_record_not_any_cached_record(self):
        portion = {"amount": 1., "gramWeight": 4.}
        rows = [{"annotation": {"gram_conversion_method": "ingredient_specific_portion", "gram_conversion_evidence": [
            {"source": "USDA", "source_ref": "1", "portion": portion}]}}]
        records = [{"record": {"fdcId": 1, "foodPortions": []}}, {"record": {"fdcId": 2, "foodPortions": [portion]}}]
        with self.assertRaises(ValueError):
            heldout.verify_portion_records(rows, records)
        records[0]["record"]["foodPortions"] = [portion]
        heldout.verify_portion_records(rows, records)

    def test_source_hash_drift_and_path_escape_fail(self):
        folder = Path(tempfile.mkdtemp(prefix="nutrition-eval-hash-test-"))
        path = folder / "source.txt"
        path.write_text("synthetic original", encoding="utf-8")
        hashes = {path.name: heldout.digest(path)}
        heldout.verify_hashes(hashes, folder)
        path.write_text("synthetic changed", encoding="utf-8")
        with self.assertRaises(ValueError):
            heldout.verify_hashes(hashes, folder)
        with self.assertRaises(ValueError):
            heldout.scoped(folder / "../outside.json", folder)

    def test_strict_json_duplicate_and_nonfinite(self):
        folder = Path(tempfile.mkdtemp(prefix="nutrition-eval-test-"))
        for index, text in enumerate(('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}')):
            path = folder / f"invalid-{index}.json"
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                heldout.read(path)

    def test_snapshot_hash_counts_duplicate_alias_ids_and_dangling_refs(self):
        invalid = snapshot()
        invalid["tables_sha256"] = "wrong"
        with self.assertRaises(ValueError):
            heldout.validate_snapshot(invalid)
        mutations = (
            lambda s: s["tables"]["ingredient_nutrition_aliases"].append(dict(s["tables"]["ingredient_nutrition_aliases"][0])),
            lambda s: s["tables"]["ingredient_nutrition_aliases"][0].update(ingredient_nutrition_id=999),
            lambda s: s["tables"]["ingredient_nutrition"][0].update(calories=True),
            lambda s: s["tables"]["ingredient_nutrition"][0].update(portion_grams={"unit": -2}),
        )
        for mutate in mutations:
            invalid = snapshot()
            mutate(invalid)
            with self.assertRaises(ValueError):
                heldout.validate_snapshot(reseal(invalid))

    def test_frozen_metadata_reviewer_time_and_convention_required(self):
        rows = [{"row_id": f"S{i}", "annotation": {"gram_conversion_method": "ingredient_specific_portion" if i < 10 else "unresolved"}} for i in range(55)]
        labels = {"schema_version": 1, "frozen": True, "mode": "independent_human_reviewed_labels_frozen", "reviewer": "synthetic reviewer",
                  "reviewed_at_utc": "2026-01-01T00:00:00Z", "rows": rows,
                  "freeze_provenance": {"label_version": "nutrition-labels-v1", "accepted_conventions": {
                      "standard_measuring_spoon_and_generic_source_identity": True, "row_ids": [f"S{i}" for i in range(10)]}}}
        proof = {"labels_sha256": "synthetic", "reviewer": labels["reviewer"], "reviewed_at_utc": labels["reviewed_at_utc"],
                 "labels_frozen": True, "freeze_ready": True, "checks": {"synthetic": True}}
        heldout.validate_freeze(labels, proof, "synthetic")
        for key, value in (("reviewer", None), ("frozen", False), ("reviewed_at_utc", "2026-01-01T00:00:00")):
            invalid = deepcopy(labels)
            invalid[key] = value
            with self.assertRaises((ValueError, TypeError)):
                heldout.validate_freeze(invalid, proof, "synthetic")
        invalid = deepcopy(labels)
        invalid["freeze_provenance"]["accepted_conventions"]["row_ids"] = []
        with self.assertRaises(ValueError):
            heldout.validate_freeze(invalid, proof, "synthetic")

    def test_tampered_label_stops_before_reading_annotations(self):
        with patch.object(heldout, "digest", return_value="tampered"), patch.object(heldout, "read") as read:
            with self.assertRaises(ValueError):
                heldout.load_bundle()
            read.assert_not_called()

    def test_memory_snapshot_uses_original_aliases_portions_and_mass_precedence(self):
        s = snapshot()
        before = deepcopy(s)
        with heldout.offline_guards(), heldout.snapshot_session(s) as db:
            self.assertIsNone(heldout.observe(db, "not an alias")["match"])
            # Thai unit suffixes work with English names; no gold aliases inserted.
            self.assertEqual(heldout.observe(db, "synthetic food 2 ช้อนชา")["grams"], 8.)
            self.assertEqual(heldout.observe(db, "synthetic food 2 กรัม")["conversion_method"], "direct_mass")
            self.assertEqual(heldout.observe(db, "synthetic food 2 มล.")["conversion_method"], "approximate")
        self.assertEqual(s, before)
        s["tables"]["ingredient_nutrition"][0]["portion_grams"] = {"กรัม": 2.}
        with heldout.offline_guards(), heldout.snapshot_session(reseal(s)) as db:
            result = heldout.observe(db, "synthetic food 2 กรัม")
            self.assertEqual(result["grams"], 4.)
            self.assertEqual(result["conversion_method"], "ingredient_specific_portion")

    def test_network_and_persistent_sqlite_attempt_fail_even_if_caught(self):
        for action in (lambda: socket.getaddrinfo("example.invalid", 443), lambda: socket.create_connection(("example.invalid", 443)),
                       lambda: sqlite3.connect("persistent-forbidden.sqlite")):
            with self.assertRaisesRegex(ValueError, "offline_guard_attempt_detected"):
                with heldout.offline_guards():
                    with self.assertRaises(RuntimeError):
                        action()

    def test_environment_file_access_denied(self):
        with self.assertRaisesRegex(ValueError, "offline_guard_attempt_detected"):
            with heldout.offline_guards():
                with self.assertRaises(RuntimeError):
                    Path(".env").read_text()

    def test_live_module_imports_denied_before_any_execution(self):
        for name in ("main", "database.db", "nutrition.seed_inmu", "nutrition.seed_usda", "nutrition.llm_fallback"):
            with self.assertRaisesRegex(ValueError, "offline_guard_attempt_detected"):
                with heldout.offline_guards():
                    with self.assertRaises(RuntimeError):
                        importlib.import_module(name)

    def test_persistent_engine_and_socket_methods_denied(self):
        from sqlalchemy import create_engine
        engine = create_engine("sqlite:///forbidden.sqlite")
        try:
            with self.assertRaisesRegex(ValueError, "offline_guard_attempt_detected"):
                with heldout.offline_guards():
                    with self.assertRaises(RuntimeError):
                        engine.connect()
            for method in ("connect", "connect_ex"):
                with self.assertRaisesRegex(ValueError, "offline_guard_attempt_detected"):
                    with heldout.offline_guards():
                        with socket.socket() as sock, self.assertRaises(RuntimeError):
                            getattr(sock, method)(("127.0.0.1", 1))
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
