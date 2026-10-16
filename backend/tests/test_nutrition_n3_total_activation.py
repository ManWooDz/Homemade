"""Synthetic pinned evidence and in-memory SQLite; no live DB or source claims."""
from copy import deepcopy
import io
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from database.models import IngredientNutrition
from eval.nutrition_heldout import observe, score
from nutrition import activate_n3_total as activation
from nutrition import activate_reviewed_herbs as herbs
from nutrition.calculator import _add_contribution, compute_quantities_nutrition, compute_recipe_nutrition
from nutrition.evidence import qualify_match
from nutrition.lookup import match_ingredient
import test_nutrition_herb_activation as herb_fixture


class N3TotalActivationTests(unittest.TestCase):
    def setUp(self):
        # Reuse the existing synthetic herb bundle, including exact approved predecessor state.
        self.fixture = herb_fixture.HerbActivationTests(methodName="runTest")
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.db = self.fixture.db
        herbs.apply_snapshot(self.db, self.fixture.snapshot())
        source = self.fixture.packet["records"][1]["artifact"]
        receipt, plan = "synthetic/n3/receipt.txt", "synthetic/n3/plan.md"
        self.fixture.blobs[receipt] = b"SYNTHETIC N3 policy approval"
        self.fixture.blobs[plan] = b"SYNTHETIC N3 implementation plan"
        self.fixture.blobs["backend/nutrition/activate_reviewed_herbs.py"] = b"SYNTHETIC herb code pin"
        calculation = {"method": activation.METHOD, "formula": activation.FORMULA, "basis": "100g",
                       "components": {key: {"value": value, "unit": "g", "basis": "100g", "source_field": field, "page": page}
                           for (key, (field, page)), value in zip(activation.COMPONENTS.items(), ("86.40", "3.27", "0.45", "1.80"))}}
        review = {"status": "accepted", "reviewer": "synthetic-reviewer", "reviewed_at_utc": "2000-01-02T00:00:00Z",
                  "receipt_ref": receipt, "receipt_sha256": self.fixture.sha(self.fixture.blobs[receipt])}
        self.packet = {"schema_version": 1, "source": "INMU", "source_ref": "N3", "source_total": None,
                       "herb_manifest_sha256": herbs.MANIFEST_SHA256, "artifact": source, "plan": plan,
                       "review": review, "calculation": calculation,
                       "artifacts": {p: self.fixture.sha(self.fixture.blobs[p])
                           for p in (source, receipt, plan, "backend/nutrition/activate_reviewed_herbs.py")}}
        self.manifest_path = "synthetic/n3/manifest.json"
        self.fixture.blobs[self.manifest_path] = self.fixture.encode(self.packet)
        self.enterContext(patch.multiple(activation, MANIFEST=self.manifest_path,
                          MANIFEST_SHA256=self.fixture.sha(self.fixture.blobs[self.manifest_path])))

    def snapshot(self):
        result = activation.preview(self.db)
        self.db.rollback()
        return result

    def repin(self, packet):
        self.fixture.blobs[self.manifest_path] = self.fixture.encode(packet)
        activation.MANIFEST_SHA256 = self.fixture.sha(self.fixture.blobs[self.manifest_path])

    def test_preview_apply_noop_restore_only_n3_changes(self):
        before = self.fixture.state()
        snapshot = self.snapshot()
        self.assertEqual(before, self.fixture.state())
        self.assertEqual(snapshot["before"]["aliases"], snapshot["after"]["aliases"])
        self.assertEqual(activation.apply_snapshot(self.db, snapshot), "applied")
        after = self.fixture.state()
        self.assertEqual(before[1], after[1])
        for old, new in zip(before[0], after[0]):
            if old["id"] != 725:
                self.assertEqual(old, new)
            else:
                self.assertEqual({k: v for k, v in old.items() if k not in ("carbs_g", "derivation")},
                                 {k: v for k, v in new.items() if k not in ("carbs_g", "derivation")})
                self.assertEqual(new["carbs_g"], 8.08)
                self.assertEqual(old["derivation"]["herb_source_correction"], new["derivation"]["herb_source_correction"])
                self.assertEqual(old["derivation"]["nutrition_evidence"]["identity"], new["derivation"]["nutrition_evidence"]["identity"])
        self.assertEqual(activation.apply_snapshot(self.db, snapshot), "noop")
        noop = self.snapshot()
        self.assertEqual(noop["before"], noop["after"])
        self.assertEqual(activation.apply_snapshot(self.db, noop), "noop")
        with self.assertRaisesRegex(ValueError, "original N3"):
            activation.restore_snapshot(self.db, noop)
        self.assertEqual(activation.restore_snapshot(self.db, snapshot), "restored")
        self.assertEqual(before, self.fixture.state())

    def test_real_lookup_calculators_estimated_not_proxy_or_fully_grounded(self):
        activation.apply_snapshot(self.db, self.snapshot())
        for alias in self.fixture.packet["records"][1]["aliases"]:
            match = match_ingredient(self.db, alias)
            self.assertEqual(match.macros.carbs_g, 8.08)
            qualification = qualify_match(alias, match)
            self.assertTrue(qualification.identity_verified)
            self.assertFalse(qualification.macros_verified)
            self.assertFalse(qualification.verified_portion_grams)
            self.assertNotIn("proxy", match.derivation)
            calculation = match.derivation["n3_total_calculation"]
            self.assertEqual(calculation["origin"], "project_derived")
            self.assertIsNone(calculation["source_total"])
            self.assertEqual(calculation["alternative_sum"], 8.14)
            self.assertEqual(calculation["discrepancy_status"], "unresolved")
        totals = {key: 0.0 for key in herbs.MACROS}
        _add_contribution(totals, match.macros, 20)
        self.assertAlmostEqual(totals["carbs_g"], 1.616)
        # Synthetic scoring only: numeric completeness must not promote derived macros.
        annotation = {"source_availability": "present", "grams": 20, "gram_conversion_method": "direct_mass",
                      "gram_conversion_source_backed": True, "proxy_status": "exact",
                      "accepted_source_rows": [{"source": "INMU", "source_ref": "N3", "unit_basis": "100g",
                                                "identity_relation": "exact"}]}
        axes = score(annotation, observe(self.db, "ใบกะเพรา 20 กรัม"))
        self.assertEqual(axes["row_identity"][0], "pass")
        self.assertEqual(axes["quantity_resolution"][0], "pass")
        self.assertEqual(axes["macro_completeness"], ("fail", "project_imputed_macros"))
        self.assertEqual(axes["proxy_free_grounded_coverage"][0], "fail")
        for grams, carbs, calories in ((100, 8.1, 41), (20, 1.6, 8.2)):
            result = compute_quantities_nutrition(self.db, [{"name": "holy basil leaves", "quantity_g": grams}], 1)
            self.assertEqual(result.nutrition["carbs_g"], carbs)
            self.assertEqual(result.nutrition["calories"], calories)
            self.assertTrue(result.partially_estimated)
            self.assertIn("derived_macros", result.partially_estimated_reasons)
            estimator = MagicMock()
            generated = compute_recipe_nutrition(self.db, [f"ใบกะเพรา {grams} กรัม"], ["ผสม"], 1, estimator)
            self.assertEqual(generated.nutrition, result.nutrition)
            self.assertTrue(generated.partially_estimated)
            self.assertTrue(any(activation.METHOD in reason for reason in generated.partially_estimated_reasons))
            estimator.estimate.assert_not_called()
        self.db.rollback()

    def test_snapshot_tampering_even_rehashed_is_rejected(self):
        snapshot = self.snapshot()
        for key, change in (("after", lambda s: s["rows"][0].update(calories=999)),
                            ("before", lambda s: s["rows"][0].update(calories=999))):
            bad = deepcopy(snapshot)
            change(bad[key])
            bad["snapshot_sha256"] = activation._digest({k: v for k, v in bad.items() if k != "snapshot_sha256"})
            with self.assertRaisesRegex(ValueError, "approved N3"):
                activation.apply_snapshot(self.db, bad)
        bad = deepcopy(snapshot)
        bad["snapshot_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "digest"):
            activation.apply_snapshot(self.db, bad)

    def test_pending_changes_basis_alias_and_macro_drift_rejected(self):
        for changes in ({"unit_basis": "100ml"}, {"calories": 42}, {"carbs_g": 8.14}, {"source_ref": "N999"}):
            with self.subTest(changes=changes):
                row = self.db.get(IngredientNutrition, 725)
                for key, value in changes.items():
                    setattr(row, key, value)
                with self.assertRaisesRegex(ValueError, "clean session"):
                    activation.preview(self.db)
                self.db.flush()
                with self.assertRaises(ValueError):
                    activation.preview(self.db)
                self.db.rollback()
        alias = self.db.query(herbs.IngredientNutritionAlias).filter_by(alias="holy basil leaves").one()
        alias.ingredient_nutrition_id = 1033
        self.db.flush()
        with self.assertRaises(ValueError):
            activation.preview(self.db)
        self.db.rollback()

    def test_missing_duplicate_row_rejected(self):
        row = self.db.get(IngredientNutrition, 725)
        self.db.delete(row)  # Synthetic in-memory fixture only.
        self.db.flush()
        with self.assertRaises(ValueError):
            activation.preview(self.db)
        self.db.rollback()
        self.db.add(IngredientNutrition(source="INMU", source_ref="N3", ingredient_name="duplicate", unit_basis="100g"))
        self.db.flush()
        with self.assertRaises(ValueError):
            activation.preview(self.db)
        self.db.rollback()

    def test_later_change_blocks_apply_and_restore(self):
        snapshot = self.snapshot()
        self.fixture.change(725, calories=42)
        with self.assertRaisesRegex(ValueError, "changed"):
            activation.apply_snapshot(self.db, snapshot)
        self.fixture.change(725, calories=41)
        activation.apply_snapshot(self.db, snapshot)
        self.fixture.change(725, calories=42)
        with self.assertRaisesRegex(ValueError, "later changes"):
            activation.restore_snapshot(self.db, snapshot)

    def test_post_write_failure_rolls_back_atomic_transition(self):
        snapshot = self.snapshot()
        before = self.fixture.state()
        original = activation.load_manifest
        with patch.object(activation, "load_manifest", side_effect=[original(), ValueError("source changed")]):
            with self.assertRaisesRegex(ValueError, "source changed"):
                activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(before, self.fixture.state())

    def test_invalid_component_values_mass_balance_and_definitions(self):
        for value in ("NaN", "Infinity", "-1", "101", "invalid", None, True, 86.4):
            bad = deepcopy(self.packet["calculation"])
            bad["components"]["water"]["value"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                activation.calculated_total(bad)
        for change in (lambda c: c.update(basis="100ml"), lambda c: c["components"].pop("ash"),
                       lambda c: c["components"]["ash"].update(source_field="CHOAVLDF"),
                       lambda c: c["components"]["water"].update(value="100")):
            bad = deepcopy(self.packet["calculation"])
            change(bad)
            with self.assertRaises(ValueError):
                activation.calculated_total(bad)

    def test_bundle_pins_source_scope_and_review_are_fail_closed(self):
        path = self.packet["artifact"]
        self.fixture.blobs[path] += b"tampered"
        with self.assertRaises(ValueError):
            activation.load_manifest()
        self.fixture.blobs[path] = self.fixture.blobs[path][:-8]
        for change in (lambda p: p.update(source_ref="N11"), lambda p: p.update(source_total=8.08),
                       lambda p: p["calculation"]["components"]["water"].update(value="86.34"),
                       lambda p: p["review"].update(status="pending")):
            bad = deepcopy(self.packet)
            change(bad)
            self.repin(bad)
            with self.assertRaises(ValueError):
                activation.preview(self.db)
            self.db.rollback()
        self.repin(self.packet)
        self.fixture.blobs[self.manifest_path] += b" "
        with self.assertRaisesRegex(ValueError, "manifest changed"):
            activation.load_manifest()

    def test_old_herb_transition_refuses_new_state_until_restored(self):
        snapshot = self.snapshot()
        activation.apply_snapshot(self.db, snapshot)
        with self.assertRaisesRegex(ValueError, "approved herb"):
            herbs.preview(self.db)
        self.db.rollback()
        activation.restore_snapshot(self.db, snapshot)
        old_preview = herbs.preview(self.db)
        self.assertEqual(old_preview["before"], old_preview["after"])
        self.db.rollback()

    def test_cli_requires_explicit_target_and_redacts_failures(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaises(SystemExit):
            activation.main(["--database-url-env", "N3_TEST_URL"])
        output = io.StringIO()
        with patch.dict("os.environ", {"N3_TEST_URL": "sqlite:///:memory:"}), redirect_stdout(output):
            self.assertEqual(activation.main(["--database-url-env", "N3_TEST_URL"]), 1)
        self.assertNotIn("sqlite", output.getvalue())
        self.assertIn('"error_type": "ValueError"', output.getvalue())

    def test_cli_default_is_read_only_preview_not_activation(self):
        engine, db = MagicMock(), MagicMock()
        engine.dialect.name = "postgresql"
        with patch.dict("os.environ", {"N3_TEST_URL": "postgresql://synthetic.invalid/test"}), \
             patch("sqlalchemy.create_engine", return_value=engine), \
             patch.object(activation, "Session") as session, \
             patch.object(activation, "preview", return_value={"status": "synthetic preview"}), \
             patch.object(activation, "apply_snapshot", side_effect=AssertionError("preview must not apply")), \
             patch.object(activation, "restore_snapshot", side_effect=AssertionError("preview must not restore")), \
             redirect_stdout(io.StringIO()):
            session.return_value.__enter__.return_value = db
            self.assertEqual(activation.main(["--database-url-env", "N3_TEST_URL"]), 0)
        db.connection.return_value.exec_driver_sql.assert_called_once_with(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        db.rollback.assert_called_once()
        db.commit.assert_not_called()
        engine.dispose.assert_called_once()

    def test_manifest_path_escape_is_rejected_before_read(self):
        packet = deepcopy(self.packet)
        packet["artifacts"]["../outside/private.txt"] = "0" * 64
        self.repin(packet)
        with self.assertRaisesRegex(ValueError, "artifact changed"):
            activation.load_manifest()


if __name__ == "__main__":
    unittest.main()
