"""Portable synthetic evidence/SQLite; real-artifact checks are explicitly separate."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, IngredientNutrition, IngredientNutritionAlias
from nutrition import activate_reviewed as activation
from nutrition.calculator import compute_recipe_nutrition
from nutrition.evidence import qualify_match
from nutrition.lookup import match_ingredient
from nutrition.text import normalize_alias
from nutrition_evidence_fixture import synthetic_evidence


class ActivationTests(unittest.TestCase):
    def evidence_context(self):
        return synthetic_evidence()

    def setUp(self):
        self.enterContext(self.evidence_context())
        self.manifest = activation.load_manifest()
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(self.engine)
        self.ids = []
        for record, alias, portions in zip(self.manifest["records"],
                ("กระเทียม", "พริกไทย", "ข้าวสวย"), ({"กลีบ": 4.0}, {"ช้อนชา": 2.0}, {"ถ้วย": 150.0})):
            row = IngredientNutrition(source=record["source"], source_ref=record["source_ref"],
                ingredient_name=record["ingredient_name"], unit_basis="100g",
                **{**record["macros"], "calories": record["legacy_energy"]}, portion_grams=portions,
                derivation={"energy_kcal": "atwater", "audit_note": {"keep": True}})
            self.db.add(row)
            self.db.flush()
            self.ids.append(row.id)
            self.db.add(IngredientNutritionAlias(alias=alias, ingredient_nutrition_id=row.id))
        self.other = IngredientNutrition(ingredient_name="sentinel prawn", source="INMU", source_ref="G4",
            unit_basis="100g", calories=88, protein_g=20, carbs_g=0, fat_g=1,
            derivation={"carbs_g": "by_difference_clamped"})
        self.db.add(self.other)
        self.db.commit()
        self.other_id = self.other.id
        self.db.rollback()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def snapshot(self):
        result = activation.preview(self.db)
        self.db.rollback()
        return result

    def rows(self):
        result = [{k: deepcopy(getattr(r, k)) for k in activation.FIELDS}
                  for r in self.db.query(IngredientNutrition).order_by(IngredientNutrition.id).all()]
        self.db.rollback()
        return result

    def change(self, index=0, **changes):
        row = self.db.get(IngredientNutrition, self.ids[index])
        for key, value in changes.items():
            setattr(row, key, value)
        self.db.commit()

    def test_manifest_exact_allowlist_source_values_and_artifact_pins(self):
        self.assertEqual([r["source_ref"] for r in self.manifest["records"]], ["N2", "N26", "A11"])
        self.assertEqual([r["macros"]["calories"] for r in self.manifest["records"]], [51, 364, 136])
        self.assertEqual(len(self.manifest["artifacts"]), 7)

    def test_preview_read_only_preserves_portions_and_unrelated_rows(self):
        before = self.rows()
        snapshot = self.snapshot()
        self.assertEqual(before, self.rows())
        for old, new in zip(snapshot["before"]["rows"], snapshot["after"]["rows"]):
            self.assertEqual(old["portion_grams"], new["portion_grams"])
            self.assertEqual(new["derivation"]["audit_note"], {"keep": True})
            self.assertNotIn("energy_kcal", new["derivation"])
        activation._check_snapshot(json.loads(json.dumps(snapshot)))

    def test_apply_idempotent_and_does_not_touch_g4(self):
        snapshot = self.snapshot()
        sentinel = self.rows()[-1]
        self.assertEqual(activation.apply_snapshot(self.db, snapshot), "applied")
        self.assertEqual(self.rows()[-1], sentinel)
        self.assertEqual(activation.apply_snapshot(self.db, snapshot), "noop")
        self.assertEqual([r["calories"] for r in self.rows()[:3]], [51, 364, 136])

    def test_approved_aliases_qualify_but_broad_aliases_and_portions_do_not(self):
        activation.apply_snapshot(self.db, self.snapshot())
        for record in self.manifest["records"]:
            for alias in record["aliases"]:
                qualification = qualify_match(alias, match_ingredient(self.db, alias))
                self.assertTrue(qualification.identity_verified and qualification.macros_verified)
                self.assertEqual(dict(qualification.verified_portion_grams), {})
        for alias in ("กระเทียม", "พริกไทย"):
            match = match_ingredient(self.db, alias)
            self.assertIsNotNone(match)
            self.assertFalse(qualify_match(alias, match).identity_verified)

    def test_calculator_direct_mass_qualified_and_household_quantity_partial(self):
        activation.apply_snapshot(self.db, self.snapshot())
        estimator = MagicMock()
        result = compute_recipe_nutrition(self.db,
            ["กระเทียมสด 100 กรัม", "พริกไทยดำบด 100 กรัม", "ข้าวสวย 100 กรัม"],
            ["ผสม"], servings=1, llm_estimator=estimator)
        self.assertFalse(result.partially_estimated, result.partially_estimated_reasons)
        self.assertEqual(result.nutrition, {"basis": "per_serving", "calories": 551.0, "protein_g": 16.8, "carbs_g": 103.7, "fat_g": 7.6})
        result = compute_recipe_nutrition(self.db, ["ข้าวสวย 1 ถ้วย"], ["ผสม"], 1, estimator)
        self.assertTrue(result.partially_estimated)
        self.assertEqual(result.nutrition["calories"], 204.0)
        estimator.estimate.assert_not_called()

    def test_drift_between_preview_and_apply_aborts_without_other_writes(self):
        for changes in ({"protein_g": 3.0}, {"portion_grams": {"กลีบ": 9.0}},
                        {"ingredient_name": "wrong fresh garlic"}, {"unit_basis": "100ml"}):
            with self.subTest(changes=changes):
                snapshot = self.snapshot()
                self.change(**changes)
                changed = self.rows()
                with self.assertRaises(ValueError):
                    activation.apply_snapshot(self.db, snapshot)
                self.assertEqual(self.rows(), changed)
                self.change(**{k: snapshot["before"]["rows"][0][k] for k in changes})

    def test_alias_state_drift_aborts(self):
        snapshot = self.snapshot()
        self.db.add(IngredientNutritionAlias(alias="fresh garlic extra", ingredient_nutrition_id=self.ids[0]))
        self.db.commit()
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.rows()[0]["calories"], 50.9)

    def test_conflicting_alias_is_not_reassigned(self):
        alias = normalize_alias(self.manifest["records"][0]["aliases"][0])
        self.db.add(IngredientNutritionAlias(alias=alias, ingredient_nutrition_id=self.other_id))
        self.db.commit()
        with self.assertRaises(ValueError):
            self.snapshot()
        self.db.rollback()
        self.assertEqual(match_ingredient(self.db, alias).ingredient_nutrition_id, self.other_id)

    def test_missing_duplicate_and_wrong_source_fail(self):
        self.change(source="USDA")
        with self.assertRaises(ValueError):
            self.snapshot()
        self.db.rollback()
        self.change(source="INMU")
        self.db.add(IngredientNutrition(ingredient_name="duplicate source ref", source="INMU", source_ref="N2"))
        self.db.commit()
        with self.assertRaises(ValueError):
            self.snapshot()

    def test_unexpected_estimate_markers_and_energy_not_cleared(self):
        for marker in ({"proxy": False}, {"carbs_g": "unknown"}, {"energy_kcal": "unknown"}):
            with self.subTest(marker=marker):
                self.change(derivation=marker)
                with self.assertRaises(ValueError):
                    self.snapshot()
                self.db.rollback()
        self.change(derivation=None, calories=50.9)
        with self.assertRaises(ValueError):
            self.snapshot()

    def test_bad_macro_and_malformed_derivation_fail(self):
        for changes in ({"carbs_g": None}, {"fat_g": -1}, {"derivation": ["atwater"]}, {"calories": None}):
            with self.subTest(changes=changes):
                original = self.rows()[0]
                self.change(**changes)
                with self.assertRaises(ValueError):
                    self.snapshot()
                self.db.rollback()
                self.change(**{k: original[k] for k in changes})

    def test_published_energy_without_old_marker_can_be_activated(self):
        self.change(calories=51, derivation={"audit_note": "retained"})
        snapshot = self.snapshot()
        activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.rows()[0]["derivation"]["audit_note"], "retained")

    def test_dirty_session_and_open_transaction_rejected(self):
        snapshot = self.snapshot()
        self.db.get(IngredientNutrition, self.ids[0]).calories = 1
        with self.assertRaises(ValueError):
            activation.preview(self.db)
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)
        self.db.rollback()
        self.db.query(IngredientNutrition).first()
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)

    def test_tampered_snapshot_rejected(self):
        snapshot = self.snapshot()
        snapshot["after"]["rows"][0]["calories"] = 99
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.rows()[0]["calories"], 50.9)

    def test_rehashed_unauthorized_transition_rejected(self):
        snapshot = self.snapshot()
        snapshot["after"]["rows"][0]["calories"] = 99
        snapshot["snapshot_sha256"] = activation._digest({k: v for k, v in snapshot.items() if k != "snapshot_sha256"})
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.rows()[0]["calories"], 50.9)

    def test_failure_after_writes_rolls_back_rows_and_aliases(self):
        snapshot = self.snapshot()
        original = activation._write_rows
        def fail_after_writes(db, state):
            original(db, state)
            db.flush()
            raise RuntimeError("synthetic late failure")
        with patch.object(activation, "_write_rows", side_effect=fail_after_writes):
            with self.assertRaises(RuntimeError):
                activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.snapshot()["before"], snapshot["before"])

    def test_failed_post_write_verification_rolls_back_alias_inserts_too(self):
        snapshot = self.snapshot()
        original = activation._state
        def fail_after_insert(db, manifest, lock=False):
            result = original(db, manifest, lock)
            if result["rows"][0]["calories"] == 51:
                raise RuntimeError("synthetic post-write failure")
            return result
        with patch.object(activation, "_state", side_effect=fail_after_insert):
            with self.assertRaises(RuntimeError):
                activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.snapshot()["before"], snapshot["before"])

    def test_restore_retains_new_aliases_but_removes_their_qualification(self):
        snapshot = self.snapshot()
        activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(activation.restore_snapshot(self.db, snapshot), "restored_rows_aliases_retained")
        restored = self.snapshot()["before"]
        self.assertEqual(restored["rows"], snapshot["before"]["rows"])
        self.assertEqual(restored["aliases"], snapshot["after"]["aliases"])
        match = match_ingredient(self.db, "กระเทียมสด")
        self.assertFalse(qualify_match("กระเทียมสด", match).identity_verified)

    def test_restore_does_not_overwrite_later_changes(self):
        snapshot = self.snapshot()
        activation.apply_snapshot(self.db, snapshot)
        self.change(portion_grams={"กลีบ": 8})
        before = self.rows()
        with self.assertRaises(ValueError):
            activation.restore_snapshot(self.db, snapshot)
        self.assertEqual(self.rows(), before)

    def test_stale_existing_evidence_rejected_and_runtime_unqualified(self):
        activation.apply_snapshot(self.db, self.snapshot())
        self.change(protein_g=3)
        match = match_ingredient(self.db, "กระเทียมสด")
        self.assertFalse(qualify_match("กระเทียมสด", match).macros_verified)
        self.db.rollback()
        with self.assertRaises(ValueError):
            self.snapshot()

    def test_snapshot_target_identity_and_truncated_rows_rejected(self):
        before = self.snapshot()["before"]
        for key, value in (("id", True), ("source", "USDA"), ("ingredient_name", "other")):
            changed = deepcopy(before)
            changed["rows"][0][key] = value
            with self.assertRaises(ValueError):
                activation._desired(changed, self.manifest)
        before["rows"].pop()
        with self.assertRaises(ValueError):
            activation._desired(before, self.manifest)

    def test_missing_or_changed_manifest_and_source_artifact_rejected(self):
        original = Path.read_bytes
        for relative in (activation.MANIFEST, self.manifest["review"]["receipt_ref"],
                         self.manifest["records"][0]["artifact"]):
            target = (activation.ROOT / relative).resolve()
            for missing in (False, True):
                with self.subTest(relative=relative, missing=missing):
                    def changed(path):
                        if path.resolve() == target:
                            if missing:
                                raise FileNotFoundError("synthetic absent artifact")
                            return b"synthetic altered bytes"
                        return original(path)
                    with patch.object(Path, "read_bytes", autospec=True, side_effect=changed):
                        with self.assertRaises((ValueError, FileNotFoundError)):
                            activation.load_manifest()

    def test_cli_default_only_previews_and_sanitizes_driver_error(self):
        engine = MagicMock()
        engine.dialect.name = "postgresql"
        output = io.StringIO()
        with patch.dict(os.environ, {"C2_TEST_URL": "synthetic://secret"}), patch("sqlalchemy.create_engine", return_value=engine), \
                patch.object(activation, "Session"), patch.object(activation, "preview", return_value={"preview": True}), \
                patch.object(activation, "apply_snapshot") as apply, patch.object(activation, "restore_snapshot") as restore, \
                redirect_stdout(output):
            self.assertEqual(activation.main(["--database-url-env", "C2_TEST_URL"]), 0)
            apply.assert_not_called()
            restore.assert_not_called()
        self.assertEqual(json.loads(output.getvalue()), {"preview": True})
        output = io.StringIO()
        with patch.dict(os.environ, {"C2_TEST_URL": "synthetic://secret"}), \
                patch("sqlalchemy.create_engine", side_effect=RuntimeError("secret password sql")), redirect_stdout(output):
            self.assertEqual(activation.main(["--database-url-env", "C2_TEST_URL"]), 1)
        self.assertNotIn("secret", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["error_type"], "RuntimeError")

    def test_cli_refuses_implicit_url_and_sqlite_before_connecting(self):
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(io.StringIO()), patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit):
                activation.main(["--database-url-env", "C2_MISSING_URL"])
        engine = MagicMock()
        engine.dialect.name = "sqlite"
        with patch.dict(os.environ, {"C2_TEST_URL": "sqlite:///:memory:"}), patch("sqlalchemy.create_engine", return_value=engine), \
                patch.object(activation, "Session") as session, redirect_stdout(io.StringIO()):
            self.assertEqual(activation.main(["--database-url-env", "C2_TEST_URL"]), 1)
            session.assert_not_called()

    def test_postgresql_write_guard_locks_both_tables_before_work(self):
        db = MagicMock()
        db.in_transaction.return_value = False
        db.new = db.dirty = db.deleted = ()
        db.get_bind.return_value.dialect.name = "postgresql"
        with activation._transaction(db):
            statements = [call.args[0] for call in db.connection.return_value.exec_driver_sql.call_args_list]
            self.assertEqual(statements, ["SET LOCAL lock_timeout = '5s'",
                "LOCK TABLE ingredient_nutrition, ingredient_nutrition_aliases IN SHARE ROW EXCLUSIVE MODE"])

    def test_existing_wrong_evidence_is_not_silently_replaced(self):
        self.change(derivation={"energy_kcal": "atwater", "nutrition_evidence": {"schema_version": 999}})
        with self.assertRaises(ValueError):
            self.snapshot()
        self.db.rollback()
        self.assertEqual(self.rows()[0]["derivation"]["nutrition_evidence"], {"schema_version": 999})


class SyntheticEvidenceIsolationTests(unittest.TestCase):
    def test_fixture_is_explicitly_synthetic_and_restores_globals_after_error(self):
        from nutrition import correct_reviewed_g4 as correction
        original = (activation.MANIFEST, activation.MANIFEST_SHA256, correction.ARTIFACTS,
                    correction.REVIEW, Path.read_bytes)
        for fail in (False, True):
            try:
                with synthetic_evidence():
                    manifest = activation.load_manifest()
                    self.assertEqual(manifest["review"]["reviewer"], "synthetic-reviewer")
                    self.assertTrue(all("example.invalid/synthetic/" in r["url"] for r in manifest["records"]))
                    self.assertEqual(correction.REVIEW["reviewer"], "synthetic-reviewer")
                    with self.assertRaises(AssertionError):
                        Path("unprovided-private-artifact.pdf").read_bytes()
                    if fail:
                        raise RuntimeError("synthetic fixture cleanup probe")
            except RuntimeError:
                self.assertTrue(fail)
            self.assertEqual((activation.MANIFEST, activation.MANIFEST_SHA256, correction.ARTIFACTS,
                              correction.REVIEW, Path.read_bytes), original)


if __name__ == "__main__":
    unittest.main()
