# Notification migration — separate local deployment approval

Status: user subsequently explicitly approved this local start/backup/migration scope. Executed successfully after exact preflight; revision b9c0d1e2f3a4 and running/healthy target independently verified. Result: notifications-migration-result-2026-10-15.md. The original source approval excluded migration; this later approval supplied it.

## Observed target (read-only)

- Existing stopped container `homemade-db-1`, exact ID `a01f9ebe86e929defd80d784a3f00930a6801dc43bf400ef65844247bafd029e`, exit0. Docker reports no running containers.
- Existing `pgvector/pgvector:pg16` image and `homemade_pgdata` volume at `/var/lib/postgresql/data`. No recreate/reset/seed/prune/new volume is proposed.
- Non-secret container identifiers and observed backend/.env agree on database/user `homemade`, backend target `localhost:5432` via `postgresql+psycopg`. No password was printed or copied.
- Live revision/schema are unknown while the DB is stopped. Expected previous source revision: `a8b9c0d1e2f3`; new revision: `b9c0d1e2f3a4`.

## Exact proposed action after approval

1. Recheck exact container/volume/image; start only this existing container and wait for readiness without changing its configuration.
2. Read-only preflight: require exactly revision `a8b9c0d1e2f3`, no notifications table and matching database/user/schema. If different, stop and amend this review; do not run older pending migrations automatically.
3. Create a fresh private custom-format pg_dump backup at a unique filename under `tmp/notifications-20261015/private/`, without overwrite. Verify saved bytes/hash and archive TOC. Retain locally outside publication; same-disk backup is not an off-device copy or restore rehearsal.
4. Apply only the reviewed Alembic upgrade to `b9c0d1e2f3a4` using the installed backend virtual environment/configuration. It adds notifications/sequence/owner FK/UNIQUE/CHECK/index and updates Alembic's version; no source ingredient, recipe or user row/seed changes.
5. Independently read back version, table/constraints/index/empty-row count; compare pre-existing schema/table counts outside the additive objects. Authenticated real application/cross-device use remains a later integration check.

No backend/frontend server restart, production deployment, package install, file/container/volume deletion, force operation or Git publication is included.

## Reviewable evidence

- Exact migration: `backend/alembic/versions/20261015_add_notifications.py`.
- Offline PostgreSQL SQL: `tmp/notifications-20261015/migration-preview.sql`, produced by `alembic upgrade a8b9c0d1e2f3:b9c0d1e2f3a4 --sql` using an unreachable dummy URL without connecting to a DB. Contains only CREATE notifications/index and the exact Alembic version UPDATE inside BEGIN/COMMIT; no DROP/DELETE/seed/older migration.
- Backend:22new guarded tests pass;87relevant existing tests pass, offline guard0. Includes isolated SQLite migration/schema comparison, concurrent event checks, owner boundaries and save/commit rollback.
- Frontend:14new tests pass; full85/89 with four existing CookingPage/quantity assertions failing. Scoped lint passes except the existing unused hasActiveFilter in UserIngredients; final2230-module build passes with existing >500kB warning. Independent UI review ship within five actual-App synthetic captures: `docs/notification-ui-review-2026-10-15.md`. Read RPC's authoritative count/local row update and semantic expiry-change guard preserve a25-row loaded range across target/back (24remaining confirmed in browser).

## Risk and recovery

New source requires the table for history/favorite notification writes. Before migration this is not a deployed/ready feature; history-save failure retains the generated recipe through the existing fallback, while favorites cannot confirm a failed save transaction. Coordinate migration before using changed source against the old schema.

The transactional additive migration can roll back before commit if it fails. After commit, retain table/history if source is reverted; automatic downgrade refuses data loss. Any later restore/table removal needs separate review. No migration proceeds under this review if the live starting revision differs.
