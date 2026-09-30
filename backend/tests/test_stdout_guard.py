# backend/tests/test_stdout_guard.py
"""stdout/stderr hardening: a print() of a non-cp874 character must never crash a request."""
import io
import os
import subprocess
import sys
import unittest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


class ImportMainStdoutTests(unittest.TestCase):
    def test_arrow_print_survives_cp874_piped_stdout(self):
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "cp874"
        proc = subprocess.run(
            [sys.executable, "-c",
             "import main; print(chr(0x2192)); print('ok')"],
            cwd=BACKEND_DIR, env=env, capture_output=True, timeout=60,
        )
        stderr = proc.stderr.decode("utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0, stderr)
        out = proc.stdout.decode("cp874", errors="replace")
        self.assertIn("\\u2192", out)
        self.assertIn("ok", out)


class HardenStdioTests(unittest.TestCase):
    def test_tolerates_streams_without_or_failing_reconfigure(self):
        import main

        class NoReconfigure:
            pass

        class Raises:
            def reconfigure(self, **kwargs):
                raise ValueError("cannot reconfigure")

        raw = io.BytesIO()
        real = io.TextIOWrapper(raw, encoding="cp874")
        main._harden_stdio([real, NoReconfigure(), Raises(), None])  # must not raise

        real.write(chr(0x2192))
        real.flush()
        self.assertEqual(raw.getvalue(), b"\\u2192")

    def test_module_hardens_real_stdio_at_import(self):
        # Under unittest stdout may be replaced; only assert when it is reconfigurable.
        import main
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                self.assertEqual(stream.errors, "backslashreplace")
        self.assertTrue(callable(main._harden_stdio))


if __name__ == "__main__":
    unittest.main()
