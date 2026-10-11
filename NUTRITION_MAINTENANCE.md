# Nutrition maintenance tests and local evidence

Default tests use synthetic in-memory evidence and isolated SQLite databases.
They test the same artifact verification, binding, transactions, rollback, no-op,
qualification and calculator paths without reading publisher PDFs or human receipts.
Synthetic reviewer/receipt/source bytes are test fixtures, not evidence of real
source accuracy, human approval, production activation or grounded coverage.

From backend/ using the project's existing Python environment:

```powershell
python tests/run_offline.py test_nutrition_*.py
```

Real-artifact integration checks are an explicit separate invocation:

```powershell
python tests/run_offline.py check_local_nutrition_evidence.py
```

That command runs the same assertions with actual artifact hash checks and only
synthetic SQLite rows. It does not contact PostgreSQL, a generator or a provider.
It fails, rather than skips, when local files are absent or changed. It is not
part of default test_*.py discovery; its separate status must be reported explicitly.

The required private bundle is the original accepted manifest at
backend/nutrition/data/accepted_c2_records.json plus its seven pinned local artifacts,
and the G4 source/receipt/original review/binding paths pinned in correct_reviewed_g4.py.
Those PDFs/receipts/bindings and accepted manifest are intentionally not published
in this slice. Keep an authorized separate backup preserving their original bytes
and relative paths; do not obtain substitute files just to make hashes pass.
Source references, expected values and hash metadata in maintenance code are not
publication of the original evidence, authentication of a reviewer or download links.

The maintenance utilities remain fail-closed and require the original bundle.
Their default CLI behavior is preview, not apply. No test fixture patches run in
normal application code. Never bypass missing artifacts, change approved hashes,
run an apply/restore/seed, or infer live-write authority from passing tests.
Each actual database transition still needs a fresh reviewed snapshot and approval.

Exact-path Git attributes preserve the pinned maintenance-module bytes across
Windows/Linux checkout without changing global Git settings. No docs allowlist,
PDF publication or deployment-secret copying is needed for default tests.

This commit does not distribute live DB contents or reproduce C2/G4 on a fresh DB.
Seeds/importers remain historical; G4's missing total carbohydrate remains partial.
Independent source QA, clinical safety, browser/provider behavior and held-out
coverage are not established by these tests.
