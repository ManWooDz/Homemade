# In-app notifications — discovery (2026-10-15 Bangkok)

Status: user confirmed the shared brief/backend source, then separately approved local DB start/backup/migration on 2026-10-15. Source verification and local migration to b9c0d1e2f3a4 complete. Real authenticated application/cross-device execution remains unverified; no server restart. See notifications-migration-result-2026-10-15.md.

## Confirmed scope

- Product envelope; no new academic contribution or KPI.
- In-app delivery when the user opens or returns to the app. Closed-app push is excluded.
- Expiry reminders plus successful recipe-save notifications. Daily recipe recommendations are excluded; the supplied Figma images are inspiration, not additional requirements.
- Near expiry: next three calendar days, including today; dates already passed receive separate wording. Use the user's recorded approximate expiry date.
- Persist notification history and read state per account, shared across devices.
- Bell to the right of the HomeMade logo on the five main tabs: Home, Fridge, Cooking entry, Favorites and Profile. Auth screens and active cooking retain their current header.
- Bell opens a dedicated notification page with unread/read tabs; rows lead to the ingredient or recipe concerned.
- Recipe saves include automatic history persistence after generation and adding catalog/generated recipes to favorites, with distinct wording. Notify only after confirmed server persistence; not on removal, duplicate addition or optimistic heart changes.
- One expiry event per ingredient/date/stage (near/today/passed); one summary toast for newly created expiry events per check. Reading suppresses repeat delivery for the same event; a later stage is a new event. First use or a gap creates only the current stage, without reconstructing missed stages.
- Use the Bangkok calendar consistently for reminders and existing expiry badges, even on devices in another timezone.
- A row becomes read on explicit activation; opening the notification page does not read it. Include an explicit Read all action. Dismissing a toast does not mark its underlying rows read.
- Changing/removing an expiry date or deleting the ingredient withdraws related obsolete reminders from both tabs and the bell count, retaining database records without silently marking them read.

## Current code evidence

- `frontend/src/App.jsx` owns shared fridge data and state-based protected-view navigation; each protected page currently renders its own logo. `HeaderLogo.jsx` serves authentication/onboarding, so changing that component alone does not reach Home.
- `frontend/src/utils/expiry.js` already uses a three-day badge threshold, nullable dates and device-local calendar arithmetic. App currently fetches fridge data on mount/API callback change, without return-to-app or midnight refresh.
- Add/edit/delete update the shared fridge array. Reminder identity and obsolete-target behavior must follow these changes.
- Thai/English use existing `useLocale()` and `translations.js`. Existing icons and motion dependencies suffice for ordinary notification UI; no new package is currently proposed.
- Generation attempts an automatic history save and returns `history_id`; generation can succeed even if history persistence fails. Both frontend generation handlers append history only with a nonnull ID. Favorites are separate explicit heart actions and update optimistically.
- No notification feed/state or central toast was found in the inspected application paths. Cross-device persistence needs an exact backend/schema/API proposal and separate confirmation under AGENTS.md.

These are source observations, not live API, browser, persistence or device verification.

## Resolved decision tree

1. In-app channel → open/return checks; no scheduler, email or closed-app push.
2. Expiry + saves → both successful history and favorite saves; no daily recommendation event.
3. Three days/today/passed → Bangkok calendar; current stage only when first observed.
4. Cross-device state → account-owned durable records; same event never recreated by concurrent checks or refresh.
5. Dedicated unread/read page → five primary-tab bells, explicit reading and read-all; date edits/deletion withdraw obsolete reminders.

The final confirmation also covers the defaults below. They are proposed implementation choices, not additional accepted user answers.

## Proposed UX with Impeccable

- Operate mode, extending the incumbent orange/white/Noto Sans Thai/430px shell. Preserve the centered logo; put a 44px labeled bell button to its right with an unread badge (visual 99+, exact accessible count).
- Notification page: Back, title, unread/read controls, newest-first rows with a restrained unread marker, actual occurrence time and explicit target. Use an expiry icon and short date wording, not a claim that the food's condition was verified. Recipe history and favorites have distinct labels.
- Keep ingredient names and meaningful dates visible; do not truncate the only identifying content. Support empty/loading/error/retry, long names, large counts and stale targets in Thai and English. Notification fetch failure must not prevent fridge or recipe use, fabricate a zero count or toast a false result.
- One accessible dismissible toast at a time inside the app shell, with an action to view the list or saved recipe. Proposed eight-second timeout pauses on hover/focus; dismissal leaves read state unchanged. Defer expiry summaries while generating/cooking or editing a form until a main tab is available. Respect reduced motion and keyboard focus; no automatic focus capture.
- No historical recipe-save backfill. Keep records without automatic deletion/retention cleanup; page the list in batches of 20 rather than loading an unlimited history. Read all applies to all active unread records, including unloaded pages. Toast presentation is transient; durable feed/read state is the recovery path if navigation/network interruption prevents a toast from being seen.
- On opening, returning to visibility or crossing Bangkok midnight while foregrounded, refresh authoritative fridge/feed state and reconcile expiry events. Also reconcile after successful fridge changes. Coalesce overlapping checks; stop hidden-tab timers. Cross-device state converges on these checks and explicit feed refresh, rather than a realtime socket.
- Returning to the notification page preserves its tab and scroll. Mark a clicked record read only after its API confirms; failed updates retain unread state and offer retry. If the target is no longer accessible, show a clear message rather than navigate to an unrelated item.

## Exact proposed implementation scope

Backend files to edit:

- `backend/database/models.py`: add one Notification model. Owner FK only; typed source references plus a bounded snapshot preserve history after a source is deleted. Fields: id/user_id/kind/event_key/target_type/target_id/payload/created_at/read_at/withdrawn_at; owner/event-key uniqueness and owner/read/order indexes.
- New `backend/alembic/versions/20261015_add_notifications.py`: additive table/index/constraint upgrade following local source head `a8b9c0d1e2f3`. No alteration of existing recipe/ingredient rows and no old-save backfill. Live migration is excluded from this approval.
- New `backend/notification_repository.py`: owned paginated reads/count, idempotent reads/read-all, Bangkok expiry reconciliation, stable event identity and withdrawal. No provider call, background process or arbitrary client-created notification payload.
- `backend/history_repository.py` and `backend/base_favorites_repository.py`: persist history/favorite notifications in the same transaction as their successful save. Existing repositories commit internally, so inserting later in main would not be atomic. A no-op favorite PUT creates no event; remove/re-add is a new actual addition. All errors roll back; preserve generation's existing fallback when history cannot be saved.
- `backend/fridge_repository.py`: withdraw obsolete expiry reminders in the edit/delete transaction; no notification-record deletion. Reverting to a previously recorded date reuses that event identity/read state, rather than producing duplicates.
- `backend/main.py`: expose owner-scoped notification list/sync/read/read-all APIs under current cookie authentication, same-origin mutation checks and bounded ID/query validation. Add optional notification metadata to successful save responses without changing existing response fields. Wire both generation routes and both favorite sources.
- New `backend/tests/test_notification_repository.py`, `backend/tests/test_notification_endpoints.py` and `backend/tests/test_notification_save_events.py`: synthetic SQLite/TestClient cases plus actual repository save-failure/concurrency semantics. Run existing history/favorites/fridge regression tests without weakening them. Any unforeseen backend-file expansion needs an amended proposal before editing.
- Necessary existing fixture reach: add Notification to isolated table lists in test_history_repository.py, test_history_endpoints.py, test_base_favorites_endpoints.py, test_fridge_repository.py and test_user_ingredients_endpoints.py. Extend base-favorite exact response expectations for approved additive metadata, retaining original status/data assertions and checking the new notification. This reconciles tests with the approved contract; no extra runtime scope.

Frontend files to edit/add:

- `frontend/src/App.jsx`: feed/return navigation, shared refresh and toast lifetime across early-return views; both generation/favorite handlers; Home bell. Do not restructure unrelated views.
- New `frontend/src/components/NotificationBell.jsx`, `NotificationToast.jsx`, `frontend/src/pages/Notifications.jsx`: accessible bell, one toast and paginated page. Reuse installed icons and existing app patterns.
- `frontend/src/pages/UserIngredients.jsx`, `CustomCookingPage.jsx`, `Favorites.jsx`, `Profile.jsx`: bell only on their primary views, passed callbacks/count from App. Active cooking, auth and profile secondary views keep current headers.
- `frontend/src/utils/expiry.js`: consistent Bangkok calendar and testable date input while preserving callers/three-day labels; no automatic ingredient selection.
- `frontend/src/utils/translations.js`: Thai/English messages and state/error labels. Optional small styles in `frontend/src/index.css` only if existing styling cannot express the result.
- New `frontend/test/notifications.test.js` and `frontend/test/expiryBangkok.test.js`: use existing node:test pattern for event/read/expiry behavior. Preserve existing favorite/profile/fridge contracts.
- Documentation: this plan, `docs/data-contracts/notifications.md`, `GLOSSARY.md`, ADR and spec verification record. No package, environment, deployment, unrelated backend or Git publication changes.

## Verification required before implementation is called complete

- Owner isolation for every endpoint, same-origin writes, bounded pagination/IDs, same-event deduplication under concurrent/repeated checks and atomic rollback when source-save/notification persistence fails.
- Missing date, three-day boundary, today/passed, first-open gap, Bangkok midnight and other device timezones; ingredient edit/delete/clear/date-revert; read-all across pages; duplicate favorite PUT/remove/re-add; both generation routes including null history_id and rollback.
- Frontend failure/retry, stale target, one summary for many ingredients, no repeat on tab navigation, toast dismissal versus read state, cooking/form deferral and account change cleanup.
- Scoped lint and focused frontend tests/build; relevant existing backend regressions and guarded source-only checks. Record any unchanged suite failures separately. Visually inspect actual UI at 320/390px and desktop, with empty/read/unread/error/long-name states and keyboard navigation, in the bounded Impeccable review workflow.
- No live DB schema or cross-device persistence claim before migration and authenticated integration are separately executed and verified. A migration proposal plus synthetic tests is not a live feature deployment.

## Risks and reversibility

The main risks are duplicate notifications/toasts, a saved claim before persistence succeeds, cross-account data exposure, stale reminders after inventory edits and interrupting active cooking. A cross-device feed introduces schema and authenticated APIs; these are more costly to reverse than a UI component. Backend edits require a concrete reviewed proposal before implementation, and live migration remains a separate action. UI changes can be reverted independently; preserve existing data and unrelated WIP.

## Next

The separately approved local migration is complete; do not request or reapply it. Run the latest app source and validate actual authenticated notification creation/read state across sessions when performing full-flow QA. Source/start/backup/migration approvals are already granted. Server restart, packages, deletion, restore and Git publication remain excluded.
