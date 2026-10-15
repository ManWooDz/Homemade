# Notifications — proposed contract (2026-10-15)

Status: implemented in authorized source, verified with synthetic SQLite/TestClient, and local PostgreSQL schema migrated/independently checked at b9c0d1e2f3a4 under separate approval. Real authenticated application/cross-device execution remains unverified; no server restart. Existing response fields remain compatible.

## Owner-scoped record

`id`, `kind`, `target_type`, `target_id`, bounded `payload` (source name and optional recorded expiry date/stage), UTC `created_at`, nullable UTC `read_at`. `withdrawn_at` is stored but withdrawn records are excluded from public lists/counts. No owner ID supplied by the client is trusted; ownership comes from authenticated cookie identity.

Kinds: `expiry_near`, `expiry_today`, `expiry_passed`, `recipe_history_saved`, `recipe_favorite_added`. Targets: `ingredient`, `history`, `base_recipe`. Clients render localized copy from typed data, never server-authored HTML. Read status, data state and toast dismissal are separate.

## APIs (source implemented; local schema ready)

UI refinement: expiry rows and single-ingredient summary toasts may display the current owned ingredient's existing `image`, joined locally by target ID. Missing/placeholder/failed images fall back to the existing icon; grouped summaries retain the bell. Images are not historical snapshots and no notification payload/schema/API field is added. The timezone helper sentence is no longer displayed; Bangkok calendar calculation/display is unchanged.

- `GET /api/notifications?state=unread|read&limit=20&before_id=...`: `{status: "success", data: {items, unread_count, next_before_id}}`. Validate state, IDs and limit (1–50); order by descending monotonically allocated ID. Pagination does not restrict unread_count.
- `POST /api/notifications/sync`: reconcile current owner fridge against today's Bangkok calendar and return `{status: "success", data: {created_items, unread_count}}`. No caller-provided ingredients, dates, names or kind. Only new current-stage expiry records appear in created_items; retry does not recreate them. Inventory edits withdraw invalid records; old-save backfill is excluded.
- `PUT /api/notifications/{id}/read`: idempotent owner-only read update; `{status: "success", data: record, unread_count}` returns the confirmed record/read timestamp and authoritative count. Unknown or other-owner ID returns 404. Clients can update the clicked row while retaining loaded pages/scroll.
- `PUT /api/notifications/read-all`: mark the owner's active unread records read, including unloaded pages; return confirmed unread_count. Existing read timestamps are preserved.

Mutations use existing same-origin protection; reads use current authentication. Failures return bounded generic error details and roll back. Lists/counts are refreshed at foreground synchronization, not broadcast in realtime across devices. Direct reads never create expiry events; explicit sync is the mutation.

## Event identity and save integration

Unique `(user_id, event_key)` enforces one event per source occurrence. Expiry identity contains ingredient ID, recorded date and current stage, not localized names or today's request timestamp. Missing dates create no reminder; first observation after a gap creates only the present stage. Edits/deletion withdraw obsolete reminders without deleting rows or setting read_at. Returning to an old recorded date reuses its identity/read state.

History identity uses the committed history row. Favorite identity uses the actual new favorite occurrence and source type; an idempotent PUT creates no new occurrence, while remove/re-add does. Preserve historical favorite notifications on removal because the earlier save did occur. Typed target resolution still validates current accessibility/ownership when opening the target.

An additive nullable top-level `notification` record on successful generation/favorite-add responses enables immediate toast handling. Generation can still succeed with null history_id when the existing history-save fallback is used; then notification is null. Primary save and its notification commit atomically in the owning repository. If either write fails, rollback prevents a false saved event. Favorite removals/no-ops have null notification. Existing clients can ignore the additional field.

Toast receipt is transient and is not proof the user read a record. Only newly created event metadata initiates an immediate toast; durable unread feed remains available after a response/navigation interruption. No autonomous retention deletion, scheduler, push or public notification payload-create endpoint is proposed.
