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
from nutrition import correct_reviewed_g4 as correction
from nutrition.calculator import compute_from_quantities, compute_recipe_nutrition
from nutrition.evidence import qualify_match
from nutrition.lookup import match_ingredient
from nutrition_evidence_fixture import synthetic_evidence


class G4CorrectionTests(unittest.TestCase):
    def evidence_context(self):
        return synthetic_evidence()

    def setUp(self):
        self.enterContext(self.evidence_context())
        self.before = correction._approved_before(correction.ROOT)
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(self.engine)
        self.db.add(IngredientNutrition(**deepcopy(self.before["rows"][0])))
        self.db.flush()
        for alias in self.before["aliases"]:
            self.db.add(IngredientNutritionAlias(alias=alias["alias"], ingredient_nutrition_id=alias["owner"]))
        self.db.add(IngredientNutrition(id=526, source="INMU", source_ref="N72", ingredient_name="synthetic sentinel",
            unit_basis="100g", calories=23, protein_g=2, carbs_g=1, fat_g=0.5, portion_grams={"synthetic": 18}))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def snapshot(self):
        result = correction.preview(self.db)
        self.db.rollback()
        return result

    def rows(self):
        from nutrition.activate_reviewed import FIELDS
        result = [{k: deepcopy(getattr(r, k)) for k in FIELDS}
                  for r in self.db.query(IngredientNutrition).order_by(IngredientNutrition.id).all()]
        self.db.rollback()
        return result

    def change(self, **values):
        row = self.db.get(IngredientNutrition, 525)
        for key, value in values.items():
            setattr(row, key, value)
        self.db.commit()

    def rehash(self, snapshot):
        snapshot["snapshot_sha256"] = correction._digest({k: v for k, v in snapshot.items() if k != "snapshot_sha256"})
        return snapshot

    def test_pins_and_preview_do_not_write(self):
        original = self.rows()
        snapshot = self.snapshot()
        self.assertEqual(original, self.rows())
        self.assertEqual(snapshot["before"], self.before)
        self.assertEqual(snapshot["after"]["aliases"], self.before["aliases"])
        self.assertEqual(len(correction.ARTIFACTS), 5)
        correction._check_snapshot(json.loads(json.dumps(snapshot)), correction.ROOT)

    def test_only_approved_values_and_derivation_change(self):
        snapshot = self.snapshot()
        before, after = (snapshot[key]["rows"][0] for key in ("before", "after"))
        self.assertEqual(after["calories"], 108)
        self.assertIsNone(after["carbs_g"])
        self.assertEqual({k: v for k, v in before.items() if k not in ("calories", "carbs_g", "derivation")},
                         {k: v for k, v in after.items() if k not in ("calories", "carbs_g", "derivation")})
        history = after["derivation"]["g4_correction"]
        self.assertEqual(history["previous_derivation"], {"carbs_g": "by_difference_clamped"})
        self.assertEqual(history["previous_macros"]["calories"], 88)
        self.assertEqual(history["previous_macros"]["carbs_g"], 0)
        self.assertEqual(history["before_state_sha256"], correction.BEFORE_SHA256)
        self.assertEqual(history["available_carbohydrate_observation"]["value"], 0.80)
        self.assertNotIn("carbs_g", after["derivation"])
        self.assertEqual({e["key"] for e in after["derivation"]["nutrition_evidence"]["macros"]},
                         {"calories", "protein_g", "fat_g"})

    def test_apply_preserves_sentinel_aliases_and_repeat_is_noop(self):
        snapshot, original = self.snapshot(), self.rows()
        self.assertEqual(correction.apply_snapshot(self.db, snapshot), "applied")
        self.assertEqual(self.rows()[1], original[1])
        self.assertEqual(correction.apply_snapshot(self.db, snapshot), "noop")
        self.assertEqual(self.snapshot()["before"], snapshot["after"])
        self.assertEqual(correction.apply_snapshot(self.db, self.snapshot()), "noop")
        self.assertEqual(self.db.query(IngredientNutritionAlias).count(), 3)

    def test_exact_identity_only_with_incomplete_macros_and_no_portions(self):
        correction.apply_snapshot(self.db, self.snapshot())
        for alias in correction.EXACT_ALIASES:
            result = qualify_match(alias, match_ingredient(self.db, alias))
            self.assertTrue(result.identity_verified)
            self.assertFalse(result.macros_verified)
            self.assertEqual(dict(result.verified_portion_grams), {})
        match = match_ingredient(self.db, "กุ้ง")
        self.assertIsNotNone(match)
        self.assertFalse(qualify_match("กุ้ง", match).identity_verified)

    def test_calculator_missing_carbs_still_partial_no_provider_or_household_factor(self):
        correction.apply_snapshot(self.db, self.snapshot())
        estimator = MagicMock()
        for name in ("กุ้งก้ามกราม, สด", "กุ้ง"):
            result = compute_recipe_nutrition(self.db, [name + " 100 กรัม"], ["ผสม"], 1, estimator)
            self.assertTrue(result.partially_estimated)
            self.assertEqual(result.nutrition, {"basis": "per_serving", "calories": 108.0,
                                              "protein_g": 17.9, "carbs_g": 0.0, "fat_g": 3.7})
            self.assertTrue(any("missing or invalid carbs_g" in r for r in result.partially_estimated_reasons))
        result = compute_recipe_nutrition(self.db, ["กุ้งก้ามกราม, สด 1 ตัว"], ["ผสม"], 1, estimator)
        self.assertTrue(result.partially_estimated)
        self.assertTrue(any("quantity" in r for r in result.partially_estimated_reasons))
        estimator.estimate.assert_not_called()
        with self.assertRaises(ValueError):
            compute_from_quantities(self.db, [{"name": "กุ้งก้ามกราม, สด", "quantity_g": 100}], 1)

    def test_current_zero_without_estimate_marker_is_not_treated_as_source_zero(self):
        self.change(derivation=None)
        with self.assertRaises(ValueError):
            self.snapshot()
        self.db.rollback()
        self.assertEqual(self.rows()[0]["carbs_g"], 0)

    def test_unexpected_current_fields_fail_without_writes(self):
        for values in ({"calories": 108}, {"carbs_g": None}, {"protein_g": 18}, {"fat_g": 4},
                       {"unit_basis": "100ml"}, {"portion_grams": {"ตัว": 20}},
                       {"source": "USDA"}, {"source_ref": "other"}, {"ingredient_name": "shrimp, cooked"},
                       {"derivation": {"proxy": False}}, {"derivation": {"carbs_g": "by_difference"}},
                       {"derivation": {"carbs_g": "by_difference_clamped", "audit": "unexpected"}},
                       {"derivation": ["invalid"]}):
            with self.subTest(values=values):
                self.change(**values)
                original = self.rows()
                with self.assertRaises(ValueError):
                    self.snapshot()
                self.db.rollback()
                self.assertEqual(self.rows(), original)
                self.change(**{k: self.before["rows"][0][k] for k in values})

    def test_wrong_id_missing_duplicate_target_fail(self):
        self.change(id=524)
        with self.assertRaises(ValueError):
            self.snapshot()
        self.db.rollback()
        row = self.db.get(IngredientNutrition, 524)
        row.id = 525
        self.db.commit()
        self.db.add(IngredientNutrition(id=527, source="INMU", source_ref="G4", ingredient_name="duplicate"))
        self.db.commit()
        with self.assertRaises(ValueError):
            self.snapshot()

    def test_alias_addition_and_conflict_fail_without_remap(self):
        self.db.add(IngredientNutritionAlias(alias="extra descriptive alias", ingredient_nutrition_id=525))
        self.db.commit()
        with self.assertRaises(ValueError):
            self.snapshot()
        self.db.rollback()
        extra = self.db.query(IngredientNutritionAlias).filter_by(alias="extra descriptive alias").one()
        extra.ingredient_nutrition_id = 526
        alias = self.db.query(IngredientNutritionAlias).filter_by(alias="กุ้ง").one()
        alias.ingredient_nutrition_id = 526
        self.db.commit()
        with self.assertRaises(ValueError):
            self.snapshot()
        self.db.rollback()
        self.assertEqual(match_ingredient(self.db, "กุ้ง").ingredient_nutrition_id, 526)

    def test_drift_between_preview_and_apply_is_rejected(self):
        snapshot = self.snapshot()
        self.change(protein_g=18)
        changed = self.rows()
        with self.assertRaises(ValueError):
            correction.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.rows(), changed)

    def test_dirty_or_open_session_is_rejected(self):
        snapshot = self.snapshot()
        self.db.get(IngredientNutrition, 525).calories = 90
        with self.assertRaises(ValueError):
            correction.preview(self.db)
        with self.assertRaises(ValueError):
            correction.apply_snapshot(self.db, snapshot)
        self.db.rollback()
        self.db.query(IngredientNutrition).first()
        with self.assertRaises(ValueError):
            correction.apply_snapshot(self.db, snapshot)

    def test_snapshot_tampering_even_rehashed_is_rejected(self):
        for section, key, value in (("after", "calories", 99), ("after", "carbs_g", 0.80),
                                    ("before", "calories", 90), ("after", "portion_grams", {"ตัว": 20})):
            with self.subTest(section=section, key=key):
                snapshot = self.snapshot()
                snapshot[section]["rows"][0][key] = value
                for rehashed in (False, True):
                    if rehashed:
                        self.rehash(snapshot)
                    with self.assertRaises(ValueError):
                        correction.apply_snapshot(self.db, snapshot)
                self.assertEqual(self.rows()[0]["calories"], 88)
        snapshot = self.snapshot()
        snapshot["schema_version"] = True
        self.rehash(snapshot)
        with self.assertRaises(ValueError):
            correction.apply_snapshot(self.db, snapshot)

    def test_stale_metadata_after_correction_stays_unqualified_and_blocks_noop(self):
        snapshot = self.snapshot()
        correction.apply_snapshot(self.db, snapshot)
        self.change(fat_g=4)
        match = match_ingredient(self.db, correction.EXACT_ALIASES[0])
        result = qualify_match(correction.EXACT_ALIASES[0], match)
        self.assertFalse(result.identity_verified or result.macros_verified)
        self.db.rollback()
        with self.assertRaises(ValueError):
            correction.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.rows()[0]["fat_g"], 4)

    def test_late_failure_rolls_back_and_preserves_aliases(self):
        snapshot = self.snapshot()
        original = correction._write_rows
        def failed_write(db, state):
            original(db, state)
            db.flush()
            raise RuntimeError("synthetic late failure")
        with patch.object(correction, "_write_rows", side_effect=failed_write):
            with self.assertRaises(RuntimeError):
                correction.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.snapshot()["before"], snapshot["before"])

    def test_post_write_failure_rolls_back(self):
        snapshot = self.snapshot()
        original = correction.preview
        def failed_postcheck(db, *args, **kwargs):
            result = original(db, *args, **kwargs)
            if result["before"]["rows"][0]["calories"] == 108:
                raise RuntimeError("synthetic post-write failure")
            return result
        with patch.object(correction, "preview", side_effect=failed_postcheck):
            with self.assertRaises(RuntimeError):
                correction.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.snapshot()["before"], snapshot["before"])

    def test_post_write_state_mismatch_rolls_back(self):
        snapshot = self.snapshot()
        original = correction.preview
        def mismatched_postcheck(db, *args, **kwargs):
            result = original(db, *args, **kwargs)
            if result["before"]["rows"][0]["calories"] == 108:
                result["before"]["rows"][0]["calories"] = 109
            return result
        with patch.object(correction, "preview", side_effect=mismatched_postcheck):
            with self.assertRaises(ValueError):
                correction.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.snapshot()["before"], snapshot["before"])

    def test_changed_or_missing_artifact_aborts_preview_and_apply(self):
        snapshot = self.snapshot()
        original = Path.read_bytes
        for relative in correction.ARTIFACTS:
            target = (correction.ROOT / relative).resolve()
            for missing in (False, True):
                with self.subTest(relative=relative, missing=missing):
                    def altered(path):
                        if path.resolve() == target:
                            if missing:
                                raise FileNotFoundError("synthetic missing evidence")
                            return b"synthetic tampered artifact"
                        return original(path)
                    with patch.object(Path, "read_bytes", autospec=True, side_effect=altered):
                        with self.assertRaises((ValueError, FileNotFoundError)):
                            self.snapshot()
                        with self.assertRaises((ValueError, FileNotFoundError)):
                            correction.apply_snapshot(self.db, snapshot)
        self.assertEqual(self.rows()[0]["calories"], 88)

    def test_cli_default_is_readonly_preview_not_apply(self):
        engine = MagicMock()
        engine.dialect.name = "postgresql"
        output = io.StringIO()
        with patch.dict(os.environ, {"G4_TEST_URL": "synthetic://not-real"}), \
                patch("sqlalchemy.create_engine", return_value=engine), patch.object(correction, "Session"), \
                patch.object(correction, "preview", return_value={"preview": True}), \
                patch.object(correction, "apply_snapshot") as apply, redirect_stdout(output):
            self.assertEqual(correction.main(["--database-url-env", "G4_TEST_URL"]), 0)
            apply.assert_not_called()
        connection = engine.connect.return_value.__enter__.return_value
        self.assertEqual([c.args[0] for c in connection.exec_driver_sql.call_args_list],
                         ["SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY", "SET LOCAL statement_timeout = '5s'"])
        connection.rollback.assert_called_once()
        self.assertEqual(json.loads(output.getvalue()), {"preview": True})

    def test_cli_refuses_implicit_url_or_sqlite_and_hides_driver_details(self):
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(io.StringIO()), patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit):
                correction.main(["--database-url-env", "G4_MISSING_URL"])
        for sqlite in (False, True):
            engine = MagicMock()
            engine.dialect.name = "sqlite"
            output = io.StringIO()
            with patch.dict(os.environ, {"G4_TEST_URL": "synthetic://secret"}), \
                    patch("sqlalchemy.create_engine", return_value=engine if sqlite else None,
                          side_effect=None if sqlite else RuntimeError("secret password SQL")), \
                    patch.object(correction, "Session") as session, redirect_stdout(output):
                self.assertEqual(correction.main(["--database-url-env", "G4_TEST_URL"]), 1)
                session.assert_not_called()
            self.assertNotIn("secret", output.getvalue())


if __name__ == "__main__":
    unittest.main()
