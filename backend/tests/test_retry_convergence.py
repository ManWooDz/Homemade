# backend/tests/test_retry_convergence.py
import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from eval import retry_convergence
from eval.allergen_kg_eval import empty_resolver, seeded_resolver
from eval.retry_convergence import check_confirmation, overall, run_arm, summarize

CASE = {
    "case_id": "c1",
    "ingredients": [{"name": "หมูสับ"}],
    "user_prefs": {"allergy": "แพ้กุ้ง"},
    "base_recipe": {"name": "x"},
}

NO_ALLERGY_CASE = {
    "case_id": "c2",
    "ingredients": [{"name": "หมูสับ"}],
    "user_prefs": {"allergy": ""},
    "base_recipe": {"name": "x"},
}


def always_shrimp(ingredients, user_prefs, base_recipe, feedback=None):
    return {
        "recipe_name": "X", "servings": 1, "adjusted_ingredients": ["กุ้ง 100 กรัม", "น้ำมัน 1 ช้อนโต๊ะ"],
        "diet_tags": ["Thai"],
        "nutrition": {"basis": "per_serving", "calories": 300, "protein_g": 20, "carbs_g": 5, "fat_g": 15},
        "instructions": ["1. ตั้งกระทะใส่น้ำมัน"], "safety_warning": "ระวัง",
    }


def _quiet():
    return contextlib.redirect_stdout(io.StringIO())


class RetryConvergenceTests(unittest.TestCase):
    def test_exhaustion_counted_per_run(self):
        with _quiet():
            rows = run_arm([CASE], empty_resolver(), always_shrimp, k=2)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["exhausted"] and r["attempts"] == 3 for r in rows))
        self.assertEqual(summarize(rows), {"c1": {"runs": 2, "exhausted": 2}})

    def test_rows_record_resolved_status_and_final_valid(self):
        with _quiet():
            floor_rows = run_arm([CASE], empty_resolver(), always_shrimp, k=1)
            kg_rows = run_arm([CASE], seeded_resolver(), always_shrimp, k=1)
            none_rows = run_arm([NO_ALLERGY_CASE], empty_resolver(), always_shrimp, k=1)
        self.assertEqual(floor_rows[0]["resolved_status"], "empty")
        self.assertEqual(kg_rows[0]["resolved_status"], "ok")
        self.assertEqual(none_rows[0]["resolved_status"], "none")
        self.assertFalse(floor_rows[0]["final_valid"])
        self.assertTrue(none_rows[0]["final_valid"])
        self.assertFalse(none_rows[0]["exhausted"])

    def test_summarize_and_overall(self):
        rows = [
            {"case_id": "a", "exhausted": True},
            {"case_id": "a", "exhausted": False},
            {"case_id": "b", "exhausted": True},
        ]
        self.assertEqual(summarize(rows), {"a": {"runs": 2, "exhausted": 1}, "b": {"runs": 1, "exhausted": 1}})
        self.assertEqual(overall(rows), {"runs": 3, "exhausted": 2})
        self.assertEqual(overall([]), {"runs": 0, "exhausted": 0})


class CheckConfirmationTests(unittest.TestCase):
    def test_returns_max_calls_when_env_matches(self):
        self.assertEqual(check_confirmation(3, 4, "72"), 72)

    def test_exits_when_unset_or_mismatched(self):
        for bad in (None, "", "71", "72 ", "abc"):
            with self.assertRaises(SystemExit, msg=repr(bad)):
                check_confirmation(3, 4, bad)

    def test_message_names_required_number(self):
        with self.assertRaises(SystemExit) as ctx:
            check_confirmation(3, 4, None)
        self.assertIn("72", str(ctx.exception))
        self.assertIn("CONFIRM_GEMINI_CALLS", str(ctx.exception))


class MainGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump([CASE, NO_ALLERGY_CASE], self.tmp, ensure_ascii=False)
        self.tmp.close()
        self.addCleanup(os.unlink, self.tmp.name)
        p = patch.object(retry_convergence, "FIXTURES_PATH", self.tmp.name)
        p.start()
        self.addCleanup(p.stop)

    def _env(self, value):
        env = {k: v for k, v in os.environ.items() if k != "CONFIRM_GEMINI_CALLS"}
        if value is not None:
            env["CONFIRM_GEMINI_CALLS"] = value
        return patch.dict(os.environ, env, clear=True)

    def _no_generator(self):
        return patch.object(retry_convergence, "_load_generator",
                            side_effect=AssertionError("generator loaded before guard passed"))

    def test_unset_env_exits_before_generator_is_loaded(self):
        with self._env(None), self._no_generator(), contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit):
                retry_convergence.main(["2", "c1"])
        self.assertIn("12", err.getvalue())  # 2 x 1 x 2 x 3 planned maximum printed

    def test_wrong_confirmation_exits_before_generator_is_loaded(self):
        with self._env("6"), self._no_generator(), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                retry_convergence.main(["2", "c1"])

    def test_unknown_case_id_exits_before_generator_is_loaded(self):
        with self._env("12"), self._no_generator(), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                retry_convergence.main(["2", "c1", "nope"])
        self.assertIn("nope", str(ctx.exception))

    def test_confirmed_run_uses_loaded_generator_only(self):
        out = io.StringIO()
        with self._env("12"), \
                patch.object(retry_convergence, "_load_generator", return_value=always_shrimp), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            report = retry_convergence.main(["2", "c1"])
        self.assertEqual(report["floor_only"]["overall"], {"runs": 2, "exhausted": 2})
        self.assertEqual(report["floor_union_kg"]["overall"], {"runs": 2, "exhausted": 2})


if __name__ == "__main__":
    unittest.main()
