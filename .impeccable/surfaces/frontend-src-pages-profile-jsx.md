---
version: 1
slug: "frontend-src-pages-profile-jsx"
primary_target: "frontend/src/pages/Profile.jsx"
related_targets: ["frontend/src/components/ProfileEditor.jsx", "frontend/src/components/NotificationBell.jsx"]
---

# Profile main

Mode: Operate. This refinement covers the main Profile landing view. Keep the existing HomeMade orange/white, self-hosted Thai font and centered430px shell. Language, history, help, preferences and editor retain their existing presentation and behavior.

- Task path: identity (avatar, display name, email, Edit), history, settings (language/preferences/help), then logout. The name/email wrap rather than truncate. No new user claims, account statistics, assets or copy.
- Structure:56px logo and44px Back/notification controls;80px avatar on white with the existing fallback. Edit belongs beside the identity. Use64px plain menu rows and dividers with flat orange icons. Per the user's follow-up, Logout retains a prominent full-width red background, white bold text and icon, pill shape and soft shadow. The compact Header option is used only by main; default Header stays unchanged for subviews.
- Scrolling: bounded native main reader with hidden scrollbar,24px end padding and89px+safe-area navigation clearance. Long names/email, retries and errors remain in the same scroll flow. Keep focus and selection in the existing dark-orange palette.
- Preserve auth/logout safeguards and navigation, avatar loading/cancellation/retry, saved notices, notification count/callback, edit/language/preferences/history/help and Cooking callbacks. Add alert semantics to the existing logout error; do not redesign the subviews or modify shared auth/editor components.
- Verification (2026-10-18): independent source assessment and parent browser/mechanical inspection;34 profile-language/history tests, scoped lint/build pass, detector JSON[]. Desktop1920px, Thai390px and English320×568 confirm wrapping without horizontal overflow, main bottom at nav top, no header-control collisions and reachable logout/error after scrolling. Synthetic checks cover edit/save notice, language change, history/preferences entry, avatar-error retry, logout failure retention and success routing to/login, notification and Cooking receipts. Receipts verify fixture callbacks, not the production router. No live account/backend mutation, physical device/avatar upload or full-suite certification.

Local proof: tmp/profile-20261018/thai-390-final.jpg, english-320-long.jpg and english-320-logout-error.jpg. No new motion or shipping raster assets.
