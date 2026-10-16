---
version: 1
slug: "notifications-20261015"
primary_target: "frontend/src/pages/Notifications.jsx"
related_targets: ["frontend/src/components/NotificationBell.jsx","frontend/src/components/NotificationToast.jsx","frontend/src/App.jsx"]
---

# Account-owned in-app notifications

Mode: Operate. User confirmed the full notification brief and scoped backend work on 2026-10-15. Extend HomeMade's incumbent white/orange, Noto Sans Thai and 430px shell; supplied Figma is inspiration, not a full-app redesign. Page composition is specified by confirmed unread/read tabs and typed rows, so no concept tournament or raster comp is required.

THESIS: Show what needs attention in the fridge and what was saved, with explicit reading and a recoverable durable list.

OWN-WORLD: Existing centered HomeMade logo, neutral white list with row separators, restrained orange unread marker and contrast-safe orange controls, native accessible icons and 44px targets. No raster asset created or changed.

STORY: Bell on five primary tabs → unread/read page → explicit row activation to the owner-authorized ingredient/recipe. One expiry summary toast leads to the page; confirmed history/favorite toasts use distinct copy. Date edits/deletion withdraw obsolete reminders.

FIRST VIEWPORT: Centered logo, Back, notification title/refresh, unread/read selector, explicit Read all and Thailand-date hint lead directly to rows. Keep names/date meaning intact at 320px; desktop retains the centered shell. Error must not look like an empty successful feed.

FORM: Code extension of the existing app. No new visual identity, comp or additional dependency. Thai/English interface; original source names stay unchanged. Toast lifetime remains in App across view returns and defers outside available main tabs.

FINISH: Inspect 390px Thai list/toast, 320px English list/error and 1366px desktop once, fix material findings together, confirm at most once, then independent finish review and incumbent-system documentation comparison. Existing DESIGN.md/design.json drift is reported, not repaired.
