"""Synthetic evidence/SQLite only; no source PDF or real reviewer is authenticated."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, IngredientNutrition, IngredientNutritionAlias
from nutrition import activate_reviewed_herbs as activation
from nutrition.calculator import compute_from_quantities, compute_recipe_nutrition
from nutrition.curated_aliases import apply_curated_aliases
from nutrition.evidence import qualify_match
from nutrition.lookup import match_ingredient
from nutrition.seed_inmu import import_csv
from nutrition.seed_usda import import_usda


class HerbActivationTests(unittest.TestCase):
    def setUp(self):
        self.blobs = {}
        receipt, inventory = "synthetic/herbs/receipt.txt", "synthetic/herbs/inventory.jsonl"
        self.blobs[receipt] = b"SYNTHETIC acceptance, not a human source review"
        self.blobs[activation.HELPER] = b"SYNTHETIC helper pin, not source code"
        review = {"status": "accepted", "reviewer": "synthetic-reviewer", "reviewed_at_utc": "2000-01-01T00:00:00Z",
                  "receipt_ref": receipt, "receipt_sha256": self.sha(self.blobs[receipt])}
        rows, aliases, records = [], [], []
        specs = (
            ("N11", 682, "ข่า", 1047, "169231", "galangal", ["ข่า", "galanga"], [],
             (35.45, 0.69, 7.79, 0.17), (35, 0.69, 7.79, 0.17), "energy_kcal", "atwater", "ENERCT"),
            ("N3", 725, "กระเพรา, ใบ", 1033, "172232", "holy basil leaves", ["กระเพรา, ใบ", "holy basil, leaves"],
             ["ใบกะเพรา", "ใบกระเพรา", "กะเพรา, ใบ"], (41, 3.27, 5.9675, 0.45), (41, 3.27, None, 0.45), "carbs_g", "by_difference", "ENERC"),
            ("N35", 728, "มะกรูด, ใบ", 1048, "167749", "kaffir lime leaves", ["มะกรูด, ใบ", "leech lime or kaffir lime, leaves"],
             ["ใบมะกรูด"], (136.58, 5.46, 21.71, 3.1), (137, 5.46, 21.71, 3.1), "energy_kcal", "atwater", "ENERCT"))
        for ref, target_id, name, proxy_id, proxy_ref, remap, retained, new, old_macros, macros, marker, method, energy_field in specs:
            source = f"synthetic/herbs/{ref}.pdf"
            self.blobs[source] = ("SYNTHETIC, NOT A PUBLISHER PDF: " + ref).encode()
            target = dict(zip(activation.FIELDS, (target_id, "INMU", ref, name, "100g", *old_macros, None, {marker: method})))
            proxy = dict(zip(activation.FIELDS, (proxy_id, "USDA", proxy_ref, remap, "100g", 80, 1, 17, 1,
                                                {"ช้อนชา": 2, "ถ้วย": 96}, {"proxy": "synthetic substitute"})))
            rows.extend([target, proxy])
            for alias in retained:
                aliases.append({"id": len(aliases) + 1, "alias": alias, "ingredient_nutrition_id": target_id})
            aliases.append({"id": len(aliases) + 1, "alias": remap, "ingredient_nutrition_id": proxy_id})
            record = {"source": "INMU", "source_ref": ref, "ingredient_name": name, "proxy_source_ref": proxy_ref,
                      "preparation": "Synthetic bounded plain ingredient, not preparation evidence",
                      "aliases": retained + [remap] + new, "remap_alias": remap, "new_aliases": new,
                      "macros": dict(zip(activation.MACROS, macros)), "energy_field": energy_field,
                      "artifact": source, "url": f"https://example.invalid/synthetic/{ref}"}
            if ref == "N3":
                record["available_carbohydrate"] = {"value": 4.04, "source_field": "CHOAVLDF", "not_runtime_total_carbohydrate": True}
            records.append(record)
        self.blobs[inventory] = b"\n".join(self.encode(part) for part in (
            {"readonly": "on", "isolation": "repeatable read"}, {}, {}, {"rows": rows, "aliases": aliases}, {}, {}))
        self.packet = {"schema_version": 1, "review": review, "inventory": inventory,
                       "artifacts": {p: self.sha(raw) for p, raw in self.blobs.items()}, "records": records}
        self.manifest_path = "synthetic/herbs/manifest.json"
        self.blobs[self.manifest_path] = self.encode(self.packet)
        self.enterContext(patch.multiple(activation, MANIFEST=self.manifest_path,
                                        MANIFEST_SHA256=self.sha(self.blobs[self.manifest_path])))

        def read_synthetic(path):
            relative = path.resolve().relative_to(activation.ROOT).as_posix()
            if relative not in self.blobs:
                raise AssertionError("Test attempted real/private artifact read")
            return self.blobs[relative]

        self.enterContext(patch.object(Path, "read_bytes", new=read_synthetic))
        self.manifest = activation.load_manifest()
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[IngredientNutrition.__table__, IngredientNutritionAlias.__table__])
        self.db = Session(self.engine, autoflush=False)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)
        for row in self.manifest["before"]["rows"]:
            self.db.add(IngredientNutrition(**deepcopy(row)))
        self.db.flush()
        for alias in aliases:
            self.db.add(IngredientNutritionAlias(**alias))
        for row_id, name, ref, alias in ((7001, "synthetic galanga flowers", "D188", "ดอกข่า"),
                                       (7002, "synthetic lime peels", "N34", "ผิวมะกรูด"),
                                       (7003, "synthetic sweet basil", "N37", "โหระพา")):
            self.db.add(IngredientNutrition(id=row_id, source="INMU", source_ref=ref, ingredient_name=name,
                                           unit_basis="100g", calories=10, protein_g=1, carbs_g=1, fat_g=1))
            self.db.flush()
            self.db.add(IngredientNutritionAlias(alias=alias, ingredient_nutrition_id=row_id))
        self.db.commit()

    @staticmethod
    def encode(value):
        return json.dumps(value, ensure_ascii=False, allow_nan=False).encode()

    @staticmethod
    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    def repin(self, packet):
        self.blobs[self.manifest_path] = self.encode(packet)
        activation.MANIFEST_SHA256 = self.sha(self.blobs[self.manifest_path])

    def snapshot(self):
        result = activation.preview(self.db)
        self.db.rollback()
        return result

    def state(self):
        result = [[{k: deepcopy(getattr(row, k)) for k in activation.FIELDS}
                   for row in self.db.query(IngredientNutrition).order_by(IngredientNutrition.id)],
                  [{"id": a.id, "alias": a.alias, "owner": a.ingredient_nutrition_id}
                   for a in self.db.query(IngredientNutritionAlias).order_by(IngredientNutritionAlias.id)]]
        self.db.rollback()
        return result

    def change(self, row_id=682, **changes):
        row = self.db.get(IngredientNutrition, row_id)
        for key, value in changes.items():
            setattr(row, key, value)
        self.db.commit()

    def test_preview_is_read_only_and_only_proposes_allowed_changes(self):
        before = self.state()
        snapshot = self.snapshot()
        self.assertEqual(before, self.state())
        self.assertEqual(len(snapshot["after"]["rows"]), 6)
        self.assertEqual(len(snapshot["before"]["aliases"]), 9)
        self.assertEqual(len(snapshot["after"]["aliases"]), 13)
        for old, new in zip(snapshot["before"]["rows"], snapshot["after"]["rows"]):
            if old["source"] == "USDA":
                self.assertEqual(old, new)
            else:
                self.assertIsNone(new["portion_grams"])
                self.assertEqual(new["derivation"]["herb_source_correction"]["before_derivation"], old["derivation"])
        activation._check_snapshot(json.loads(json.dumps(snapshot)), self.manifest)

    def test_float_binding_preserves_integer_spelled_source_bytes_and_preview_digest(self):
        inventory = self.packet["inventory"]
        raw = self.blobs[inventory]
        source_rows = json.loads(raw.splitlines()[3])["rows"]
        self.assertIs(type(next(r for r in source_rows if r["id"] == 725)["calories"]), int)
        snapshot = self.snapshot()
        self.assertIs(type(next(r for r in snapshot["before"]["rows"] if r["id"] == 725)["calories"]), float)
        for row in snapshot["after"]["rows"]:
            if row["source"] == "INMU":
                for key in activation.MACROS:
                    self.assertTrue(row[key] is None or type(row[key]) is float)
        self.assertEqual(self.blobs[inventory], raw)
        activation._check_snapshot(json.loads(self.encode(snapshot)), self.manifest)

    def test_apply_exact_changes_and_noop_preserve_controls_and_proxy_rows(self):
        before = self.state()
        snapshot = self.snapshot()
        self.assertEqual(activation.apply_snapshot(self.db, snapshot), "applied")
        after = self.state()
        self.assertEqual(len(after[0]), len(before[0]))
        self.assertEqual(len(after[1]), len(before[1]) + 4)
        for old, new in zip(before[0], after[0]):
            if old["id"] not in (682, 725, 728):
                self.assertEqual(old, new)
        remaps = {"galangal": 682, "holy basil leaves": 725, "kaffir lime leaves": 728}
        self.assertEqual(sum(a != b for a, b in zip(before[1], after[1][:len(before[1])])), 3)
        for alias, owner in remaps.items():
            self.assertEqual(match_ingredient(self.db, alias).ingredient_nutrition_id, owner)
        self.db.rollback()
        self.assertEqual(activation.apply_snapshot(self.db, snapshot), "noop")
        noop_preview = self.snapshot()
        self.assertEqual(noop_preview["before"], noop_preview["after"])
        self.assertEqual(activation.apply_snapshot(self.db, noop_preview), "noop")
        self.assertEqual(after, self.state())

    def test_identity_macros_and_portions_are_separate_for_all_thirteen_aliases(self):
        activation.apply_snapshot(self.db, self.snapshot())
        for record in self.manifest["records"]:
            for alias in record["aliases"]:
                match = match_ingredient(self.db, alias)
                qualification = qualify_match(alias, match)
                self.assertTrue(qualification.identity_verified)
                self.assertEqual(qualification.macros_verified, record["source_ref"] != "N3")
                self.assertEqual(dict(qualification.verified_portion_grams), {})
                self.assertIsNone(match.portion_grams)
                self.assertNotIn("proxy", match.derivation)
                self.assertNotIn("energy_kcal", match.derivation)
                self.assertNotIn("carbs_g", match.derivation)
        match = match_ingredient(self.db, "ใบกะเพรา")
        self.assertIsNone(match.macros.carbs_g)
        self.assertEqual(len(match.derivation["nutrition_evidence"]["macros"]), 3)
        self.assertEqual(match.derivation["herb_source_correction"]["available_carbohydrate_not_total"]["value"], 4.04)

    def test_calculator_direct_mass_partial_n3_and_no_proxy_portion_transfer(self):
        activation.apply_snapshot(self.db, self.snapshot())
        estimator = MagicMock()
        result = compute_recipe_nutrition(self.db, ["ข่า 100 กรัม", "ใบมะกรูด 100 กรัม"], ["ผสม"], 1, estimator)
        self.assertFalse(result.partially_estimated, result.partially_estimated_reasons)
        self.assertEqual(result.nutrition["calories"], 172)
        result = compute_recipe_nutrition(self.db, ["ใบกะเพรา 100 กรัม"], ["ผสม"], 1, estimator)
        self.assertTrue(result.partially_estimated)
        self.assertEqual(result.nutrition["calories"], 41)
        self.assertTrue(any("missing or invalid carbs_g" in reason for reason in result.partially_estimated_reasons))
        result = compute_recipe_nutrition(self.db, ["ข่า 1 ช้อนชา"], ["ผสม"], 1, estimator)
        self.assertTrue(result.partially_estimated)
        self.assertEqual(result.nutrition["calories"], 1.8)  # Legacy global 5g, not substitute ginger's2g.
        result = compute_recipe_nutrition(self.db, ["ใบมะกรูด 1 ใบ"], ["ผสม"], 1, estimator)
        self.assertTrue(result.partially_estimated)
        estimator.estimate.assert_not_called()
        self.assertEqual(compute_from_quantities(self.db, [{"name": "galangal", "quantity_g": 100}], 1)["calories"], 35)
        with self.assertRaisesRegex(ValueError, "carbs_g"):
            compute_from_quantities(self.db, [{"name": "holy basil leaves", "quantity_g": 100}], 1)

    def test_broad_or_other_part_aliases_are_not_certified_or_remapped(self):
        before = self.state()
        activation.apply_snapshot(self.db, self.snapshot())
        for alias, row_id in (("ดอกข่า", 7001), ("ผิวมะกรูด", 7002), ("โหระพา", 7003)):
            match = match_ingredient(self.db, alias)
            self.assertEqual(match.ingredient_nutrition_id, row_id)
            self.assertFalse(qualify_match(alias, match).identity_verified)
        for alias in ("กะเพรา", "กระเพรา", "มะกรูด", "ข่าแห้ง", "galangal powder"):
            self.assertIsNone(match_ingredient(self.db, alias))
        self.db.rollback()
        self.assertEqual(before[0][-3:], self.state()[0][-3:])

    def test_dirty_pending_and_open_transaction_rejected(self):
        snapshot = self.snapshot()
        self.db.get(IngredientNutrition, 682).calories = 99
        with self.assertRaises(ValueError):
            activation.preview(self.db)
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)
        self.db.rollback()
        self.db.add(IngredientNutrition(ingredient_name="pending synthetic row"))
        with self.assertRaises(ValueError):
            activation.preview(self.db)
        self.db.rollback()
        self.db.query(IngredientNutrition).first()
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)
        self.db.rollback()

    def test_selected_row_drift_rejects_without_any_other_write(self):
        snapshot = self.snapshot()
        for changes in ({"calories": 99}, {"portion_grams": {"ใบ": 1}}, {"derivation": {"nutrition_evidence": None}},
                        {"derivation": {"herb_source_correction": {}}}, {"unit_basis": "100ml"},
                        {"source": "USDA"}, {"ingredient_name": "wrong plant"}):
            with self.subTest(changes=changes):
                self.change(**changes)
                changed = self.state()
                with self.assertRaises(ValueError):
                    activation.apply_snapshot(self.db, snapshot)
                self.assertEqual(changed, self.state())
                original = snapshot["before"]["rows"][0]
                self.change(**{k: deepcopy(original[k]) for k in changes})
        self.change(1047, calories=99)
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)

    def test_duplicate_source_code_rejected(self):
        self.db.add(IngredientNutrition(ingredient_name="duplicate synthetic galanga", source="INMU", source_ref="N11"))
        self.db.commit()
        with self.assertRaises(ValueError):
            self.snapshot()

    def test_added_alias_conflict_and_original_alias_id_drift_rejected(self):
        snapshot = self.snapshot()
        self.db.add(IngredientNutritionAlias(alias="ใบกะเพรา", ingredient_nutrition_id=7003))
        self.db.commit()
        changed = self.state()
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(changed, self.state())
        with self.assertRaises(ValueError):
            self.snapshot()
        self.db.rollback()
        original = self.db.query(IngredientNutritionAlias).filter_by(alias="galangal").one()
        original.id = 9999
        self.db.commit()
        with self.assertRaises(ValueError):
            self.snapshot()

    def test_alias_owner_and_unapproved_incoming_alias_drift_rejected(self):
        snapshot = self.snapshot()
        alias = self.db.query(IngredientNutritionAlias).filter_by(alias="galangal").one()
        alias.ingredient_nutrition_id = 7003
        self.db.commit()
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)
        alias = self.db.query(IngredientNutritionAlias).filter_by(alias="galangal").one()
        alias.ingredient_nutrition_id = 1047
        self.db.add(IngredientNutritionAlias(alias="unapproved incoming synthetic alias", ingredient_nutrition_id=682))
        self.db.commit()
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)

    def test_tampered_even_rehashed_snapshot_cannot_define_new_transition(self):
        snapshot = self.snapshot()
        for part in ("before", "after"):
            saved = deepcopy(snapshot)
            saved[part]["rows"][0]["calories"] = 999
            saved["snapshot_sha256"] = activation._digest({k: v for k, v in saved.items() if k != "snapshot_sha256"})
            with self.assertRaises(ValueError):
                activation.apply_snapshot(self.db, saved)
        saved = deepcopy(snapshot)
        saved["schema_version"] = True
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, saved)
        saved = deepcopy(snapshot)
        saved["snapshot_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, saved)

    def test_flush_and_post_write_failures_roll_back_rows_and_aliases(self):
        before, snapshot = self.state(), self.snapshot()
        with patch.object(self.db, "flush", side_effect=RuntimeError("synthetic flush failure")):
            with self.assertRaises(RuntimeError):
                activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(before, self.state())
        wrong = deepcopy(snapshot["after"])
        wrong["rows"][0]["calories"] = 999
        with patch.object(activation, "_state", side_effect=[snapshot["before"], wrong]):
            with self.assertRaises(ValueError):
                activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(before, self.state())

    def test_source_pin_drift_during_write_causes_transaction_rollback(self):
        snapshot, before = self.snapshot(), self.state()
        source = self.packet["records"][0]["artifact"]
        original, flush = self.blobs[source], self.db.flush

        def tamper_after_flush():
            flush()
            self.blobs[source] = b"SYNTHETIC changed source"

        with patch.object(self.db, "flush", new=tamper_after_flush):
            with self.assertRaises(ValueError):
                activation.apply_snapshot(self.db, snapshot)
        self.blobs[source] = original
        self.assertEqual(before, self.state())

    def test_restore_returns_original_rows_and_owners_but_retains_new_aliases(self):
        before, snapshot = self.state(), self.snapshot()
        activation.apply_snapshot(self.db, snapshot)
        self.assertEqual(activation.restore_snapshot(self.db, snapshot), "restored_rows_and_owners_new_aliases_retained")
        restored = self.state()
        self.assertEqual(before[0], restored[0])
        self.assertEqual(before[1], restored[1][:len(before[1])])
        self.assertEqual(len(restored[1]), len(before[1]) + 4)
        match = match_ingredient(self.db, "ใบกะเพรา")
        self.assertFalse(qualify_match("ใบกะเพรา", match).identity_verified)
        self.assertIn("carbs_g", match.derivation)
        self.db.rollback()
        with self.assertRaises(ValueError):
            activation.apply_snapshot(self.db, snapshot)

    def test_restore_refuses_later_drift_or_noop_snapshot(self):
        snapshot = self.snapshot()
        activation.apply_snapshot(self.db, snapshot)
        noop = self.snapshot()
        with self.assertRaises(ValueError):
            activation.restore_snapshot(self.db, noop)
        self.change(calories=99)
        changed = self.state()
        with self.assertRaises(ValueError):
            activation.restore_snapshot(self.db, snapshot)
        self.assertEqual(changed, self.state())

    def test_manifest_and_each_artifact_pin_reject_tamper(self):
        for path in [self.manifest_path, *self.packet["artifacts"]]:
            with self.subTest(path=path):
                original = self.blobs[path]
                self.blobs[path] = original + b"SYNTHETIC changed bytes"
                with self.assertRaises(ValueError):
                    activation.load_manifest()
                self.blobs[path] = original

    def test_path_escape_and_bad_allowlist_rejected_before_any_external_read(self):
        packet = deepcopy(self.packet)
        packet["artifacts"]["../outside.pdf"] = "0" * 64
        self.repin(packet)
        with self.assertRaises(ValueError):
            activation.load_manifest()
        with patch.object(activation, "MANIFEST", "../outside.json"):
            with self.assertRaises(ValueError):
                activation.load_manifest()
        packet = deepcopy(self.packet)
        packet["records"][0]["source_ref"] = "D188"
        self.repin(packet)
        with self.assertRaises(ValueError):
            activation.load_manifest()

    def test_invalid_review_or_available_carb_substitution_cannot_qualify(self):
        for change in ("review", "carbs"):
            packet = deepcopy(self.packet)
            if change == "review":
                packet["review"]["status"] = "draft"
            else:
                packet["records"][1]["macros"]["carbs_g"] = 4.04
            self.repin(packet)
            with self.assertRaises(ValueError):
                self.snapshot()
            self.db.rollback()

    def test_existing_importers_do_not_overwrite_or_reclaim_reviewed_rows(self):
        activation.apply_snapshot(self.db, self.snapshot())
        before = self.state()
        remote = MagicMock()
        self.change(1047, carbs_g=None)  # Force the actual refresh branch, not current-row skip.
        changed = self.state()
        with self.assertRaises(ValueError):
            import_usda(self.db, remote, "synthetic-key", {"galangal": 169231})
        remote.get.assert_not_called()
        self.db.rollback()
        self.assertEqual(changed, self.state())
        with self.assertRaises(ValueError):
            apply_curated_aliases(self.db, [{"alias": "galangal", "food_code": "169231"}])
        self.db.rollback()
        self.assertEqual(changed, self.state())
        csv_text = "Food_Code,Thai_Name\nN11,ข่า\nN3,\"กระเพรา, ใบ\"\nN35,\"มะกรูด, ใบ\"\n"
        with patch("builtins.open", return_value=io.StringIO(csv_text)):
            self.assertEqual(import_csv(self.db, "synthetic.csv")["imported"], 0)
        self.assertEqual(changed, self.state())
        self.assertEqual(before[0][0], self.state()[0][0])

    def test_cli_requires_explicit_target_and_redacts_driver_errors(self):
        with patch.dict(os.environ, SYNTHETIC_HERB_DB_URL=""), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as missing:
                activation.main(["--database-url-env", "SYNTHETIC_HERB_DB_URL"])
        self.assertEqual(missing.exception.code, 2)
        with patch.dict(os.environ, SYNTHETIC_HERB_DB_URL="postgresql://synthetic-secret@test.invalid/test"), \
                patch("sqlalchemy.create_engine", side_effect=RuntimeError("driver leaked synthetic-secret")), \
                redirect_stdout(io.StringIO()) as output:
            self.assertEqual(activation.main(["--database-url-env", "SYNTHETIC_HERB_DB_URL"]), 1)
        self.assertEqual(json.loads(output.getvalue()), {"status": "failed", "error_type": "RuntimeError"})
        self.assertNotIn("synthetic-secret", output.getvalue())

    def test_cli_rejects_sqlite_before_connection(self):
        with patch.dict(os.environ, SYNTHETIC_HERB_DB_URL="sqlite:///:memory:"), \
                redirect_stdout(io.StringIO()) as output:
            self.assertEqual(activation.main(["--database-url-env", "SYNTHETIC_HERB_DB_URL"]), 1)
        self.assertEqual(json.loads(output.getvalue()), {"status": "failed", "error_type": "ValueError"})

    def test_cli_preview_sets_postgresql_read_only_and_rolls_back(self):
        engine, db = MagicMock(), MagicMock()
        engine.dialect.name = "postgresql"
        with patch.dict(os.environ, SYNTHETIC_HERB_DB_URL="postgresql://synthetic.invalid/test"), \
                patch("sqlalchemy.create_engine", return_value=engine), \
                patch.object(activation, "Session") as session, \
                patch.object(activation, "preview", return_value={"preview": "synthetic"}), \
                redirect_stdout(io.StringIO()) as output:
            session.return_value.__enter__.return_value = db
            self.assertEqual(activation.main(["--database-url-env", "SYNTHETIC_HERB_DB_URL"]), 0)
        self.assertEqual(json.loads(output.getvalue()), {"preview": "synthetic"})
        db.connection.return_value.exec_driver_sql.assert_called_once_with("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        db.rollback.assert_called_once()
        engine.dispose.assert_called_once()

    def test_fresh_import_has_no_implicit_db_or_dotenv_access(self):
        code = """import socket, dotenv, sys
def forbidden(*a, **k): raise AssertionError('implicit side effect')
socket.socket.connect = forbidden
dotenv.load_dotenv = forbidden
from nutrition import activate_reviewed_herbs
assert 'database.db' not in sys.modules
assert 'main' not in sys.modules
print('fresh import no implicit DB/dotenv: pass')
"""
        result = subprocess.run([sys.executable, "-c", code], cwd=activation.ROOT / "backend",
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fresh import no implicit DB/dotenv: pass", result.stdout)


if __name__ == "__main__":
    unittest.main()
