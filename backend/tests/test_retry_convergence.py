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


def erroring(ingredients, user_prefs, base_recipe, feedback=None):
    return {"error": "boom", "details": "quota exceeded"}


def erroring_no_details(ingredients, user_prefs, base_recipe, feedback=None):
    return {"error": "boom"}


def _quiet():
    return contextlib.redirect_stdout(io.StringIO())


class RetryConvergenceTests(unittest.TestCase):
    def test_exhaustion_counted_per_run(self):
        with _quiet():
            rows = run_arm([CASE], empty_resolver(), always_shrimp, k=2)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["exhausted"] and r["attempts"] == 3 for r in rows))
        self.assertEqual(summarize(rows), {"c1": {"runs": 2, "exhausted": 2, "errored": 0, "passed": 0}})

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

    def test_resolved_statuses_records_every_flagged_key(self):
        case = dict(CASE, case_id="multi", user_prefs={"allergy": "แพ้กุ้งและนม"})
        with _quiet():
            rows = run_arm([case], seeded_resolver(), always_shrimp, k=1)
        statuses = rows[0]["resolved_statuses"]
        self.assertGreaterEqual(len(statuses), 2)
        self.assertEqual(set(statuses.values()), {"ok"})
        self.assertEqual(rows[0]["resolved_status"], "ok")

    def test_error_dict_is_errored_not_exhausted(self):
        with _quiet():
            rows = run_arm([CASE], empty_resolver(), erroring, k=1)
            rows2 = run_arm([CASE], empty_resolver(), erroring_no_details, k=1)
            ok_rows = run_arm([NO_ALLERGY_CASE], empty_resolver(), always_shrimp, k=1)
        self.assertTrue(rows[0]["errored"])
        self.assertFalse(rows[0]["exhausted"])
        self.assertFalse(rows[0]["final_valid"])
        self.assertEqual(rows[0]["error_details"], "quota exceeded")
        self.assertEqual(rows2[0]["error_details"], "boom")
        self.assertEqual(summarize(rows), {"c1": {"runs": 1, "exhausted": 0, "errored": 1, "passed": 0}})
        self.assertFalse(ok_rows[0]["errored"])
        self.assertIsNone(ok_rows[0]["error_details"])

    def test_summarize_and_overall(self):
        def row(case_id, exhausted=False, errored=False, passed=False):
            return {"case_id": case_id, "exhausted": exhausted, "errored": errored, "final_valid": passed}
        rows = [row("a", exhausted=True), row("a", passed=True), row("b", exhausted=True), row("b", errored=True)]
        self.assertEqual(summarize(rows), {
            "a": {"runs": 2, "exhausted": 1, "errored": 0, "passed": 1},
            "b": {"runs": 2, "exhausted": 1, "errored": 1, "passed": 0},
        })
        self.assertEqual(overall(rows), {"runs": 4, "exhausted": 2, "errored": 1, "passed": 1})
        self.assertEqual(overall([]), {"runs": 0, "exhausted": 0, "errored": 0, "passed": 0})


class CheckConfirmationTests(unittest.TestCase):
    def test_returns_max_calls_when_env_matches(self):
        self.assertEqual(check_confirmation(3, 4, "72"), 72)

    def test_exits_when_unset_or_mismatched(self):
        for bad in (None, "", "71", "72 ", "abc"):
            with self.assertRaises(SystemExit, msg=repr(bad)):
                check_confirmation(3, 4, bad)

    def test_exits_when_k_or_cases_below_one(self):
        for k, n in ((0, 4), (3, 0), (-1, 4), (0, 0)):
            with self.assertRaises(SystemExit, msg=(k, n)):
                check_confirmation(k, n, "0")

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

    def _cleanup_files(self, *paths):
        for path in paths:
            self.addCleanup(lambda p=path: os.path.exists(p) and os.unlink(p))

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

    def test_graph_status_assertion_runs_before_confirmation_and_generator(self):
        with self._env(None), self._no_generator(), \
                patch.object(retry_convergence, "assert_graph_status", side_effect=RuntimeError("bad graph")), \
                patch.object(retry_convergence, "check_confirmation",
                             side_effect=AssertionError("confirmation checked before status assertion")), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(RuntimeError):
                retry_convergence.main(["2", "c1"])

    def test_confirmed_run_uses_loaded_generator_only(self):
        with self._env("12"), \
                patch.object(retry_convergence, "_load_generator", return_value=always_shrimp), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            report = retry_convergence.main(["2", "c1"])
        expected = {"runs": 2, "exhausted": 2, "errored": 0, "passed": 0}
        self.assertEqual(report["floor_only"]["overall"], expected)
        self.assertEqual(report["floor_union_kg"]["overall"], expected)

    def test_stdout_is_only_parseable_json_despite_progress_prints(self):
        out, err = io.StringIO(), io.StringIO()
        with self._env("12"), \
                patch.object(retry_convergence, "_load_generator", return_value=always_shrimp), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            retry_convergence.main(["2", "c1"])
        parsed = json.loads(out.getvalue())
        self.assertEqual(set(parsed), {"floor_only", "floor_union_kg"})
        self.assertIn("Generation Attempt", err.getvalue())  # progress went to stderr

    def test_out_option_writes_report_file_and_partial(self):
        out_path = self.tmp.name + ".report.json"
        self._cleanup_files(out_path, out_path + ".partial.json")
        out = io.StringIO()
        with self._env("12"), \
                patch.object(retry_convergence, "_load_generator", return_value=always_shrimp), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            retry_convergence.main(["--out", out_path, "2", "c1"])
        self.assertEqual(out.getvalue(), "")
        with open(out_path, encoding="utf-8") as f:
            self.assertEqual(set(json.load(f)), {"floor_only", "floor_union_kg"})
        self.assertTrue(os.path.exists(out_path + ".partial.json"))

    def test_partial_file_survives_crash_in_second_arm(self):
        out_path = self.tmp.name + ".crash.json"
        self._cleanup_files(out_path, out_path + ".partial.json")
        first_rows = [{"case_id": "c1", "run": 1, "exhausted": True, "errored": False, "final_valid": False}]
        calls = []

        def fake_run_arm(cases, resolve, generate_fn, k):
            calls.append(1)
            if len(calls) == 2:
                raise ConnectionError("second arm died")
            return first_rows

        with self._env("6"), \
                patch.object(retry_convergence, "_load_generator", return_value=always_shrimp), \
                patch.object(retry_convergence, "run_arm", side_effect=fake_run_arm), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(ConnectionError):
                retry_convergence.main(["--out", out_path, "1", "c1"])
        with open(out_path + ".partial.json", encoding="utf-8") as f:
            partial = json.load(f)
        self.assertEqual(partial["floor_only"]["overall"]["exhausted"], 1)
        self.assertNotIn("floor_union_kg", partial)
        self.assertFalse(os.path.exists(out_path))

    def test_errored_rows_still_write_report_then_exit_3_with_warning(self):
        out, err = io.StringIO(), io.StringIO()
        with self._env("12"), \
                patch.object(retry_convergence, "_load_generator", return_value=erroring), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as ctx:
                retry_convergence.main(["2", "c1"])
        self.assertEqual(ctx.exception.code, 3)
        parsed = json.loads(out.getvalue())
        self.assertEqual(parsed["floor_only"]["overall"]["errored"], 2)
        self.assertEqual(parsed["floor_only"]["overall"]["exhausted"], 0)
        self.assertIn("c1", err.getvalue())
        self.assertIn("quota exceeded", err.getvalue())


if __name__ == "__main__":
    unittest.main()
