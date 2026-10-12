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
Seeds/importers still contain historical inputs; G4's missing total carbohydrate remains partial.
Independent source QA, clinical safety, browser/provider behavior and held-out
coverage are not established by these tests.

## Preserving reviewed rows during import

Ordinary USDA refresh, portion backfill and curated alias writes protect any row
whose derivation contains nutrition_evidence or g4_correction, even if that value
is partial, stale or malformed. This is preservation, not evidence qualification.
Protected USDA refresh raises ValueError before fetching; portion additions or
changes and alias remaps involving a protected owner or target require a separate
review. Identical portions/same-owner aliases remain no-ops. New aliases may be
added without adding certified identity entries; qualification rules are unchanged.

Each function preflights its batch before its own mutations, including duplicate
curated alias intents. Food codes resolving to multiple rows raise ValueError
rather than selecting the first row. Unambiguous non-reviewed rows retain their
existing behavior and result shapes; processed no-ops retain the existing counts.
There is no bypass flag or atomic transaction across USDA's two CLI functions.
Use a dedicated maintenance session; this does not suppress caller-owned pending
changes, direct SQL, concurrent external writers or deletion/recreation of a DB.

INMU import already skips existing ingredient names and preserves existing aliases.
These guards do not activate reviewed records on an empty DB or certify legacy
values. Fresh-DB activation and any live transition still need a separately
reviewed snapshot and the original private evidence bundle.

## Bounded herb source activation

nutrition.activate_reviewed_herbs is a separate pinned N11/N3/N35 utility.
It reuses the existing transaction/hash helpers without changing C2/G4 pins.
Its private accepted_herb_records.json binds three original PDFs, a new human
acceptance receipt, the approved plan, original six-row/nine-alias inventory and
the unchanged helper module. Missing or changed bytes fail closed; default tests
substitute entirely synthetic evidence, never real PDFs or acceptance claims.

The default CLI operation is a PostgreSQL repeatable-read/read-only preview using
an explicitly named environment variable holding the target URL. It neither loads
.env nor derives a target implicitly. Existing --apply-snapshot/--restore-snapshot
patterns are explicit write operations and require separate reviewed live authority.
Do not treat approval to implement/test the utility as permission to use them.

Only three INMU rows and thirteen exact aliases are in scope: six retained,
three English owner remaps and four leaf-specific Thai additions. USDA substitute
rows/portions remain comparison controls and are never written or transferred.
N11/N35 retain source-published integer energy; N3 total carbohydrate becomes
NULL, not available carbohydrate or a new project completion, and remains partial.
No new portion is certified. Plain named-ingredient conventions do not establish
unlisted parts, botanical species, dry/powder/product variants or source raw status.

Apply checks the reviewed before/after transition under the existing table-locking
transaction, checks source pins again before commit, and refuses drift; repeating
the original snapshot after identical success is a no-op. Restore requires the
original transition snapshot and no later selected-state changes, restores the
three INMU rows and original English alias owners, but retains four added aliases
numerical-only rather than deleting them. This is not full-database rollback.
After such restoration the retained aliases differ from the original inventory;
reapplying needs a new reviewed transition, not a bypass or removal command.

Use the same offline runner with test_nutrition_herb_activation.py for synthetic
transaction, tamper, caller and maintenance-preservation checks. Real-bundle
verification and read-only live preview are separate checks, not source truth or
coverage improvement. No fresh historical seed correction, automatic startup,
provider fetch, DB reset or private-source publication is introduced.

Do not automatically recompute/reseed base recipes after activation. The strict
compute_from_quantities helper correctly rejects incomplete N3; seed_postgres.seed
catches that error and writes its hand-typed fallback for affected recipes.
This utility does not touch stored base_recipe nutrition or make that fallback
grounded. Review that separate seed workflow before using it with partial rows.
