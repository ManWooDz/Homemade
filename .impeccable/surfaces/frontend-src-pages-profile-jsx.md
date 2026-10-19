---
version: 1
slug: "frontend-src-pages-profile-jsx"
primary_target: "frontend/src/pages/Profile.jsx"
related_targets: ["frontend/src/components/ProfileEditor.jsx", "frontend/src/components/NotificationBell.jsx"]
---

# Profile main

## Preference editor refinement (2026-10-20)

Mode: Operate. The user separately authorized refinement of view=preferences; this expands the earlier main-only brief for this subview. Keep the430px shell, Thai font, orange/white identity, choice values and all persistence handlers. Scope new CSS to the preference editor's unique classes.

- Reading path remains age, cuisine, allergies, dietary choices, equipment, frequency and goals. Left-aligned44px choices use12px horizontal padding,14px control labels and blush/dark-orange selected states; custom inputs remain16px. Use16px semibold section headings,24px spacing and thin dividers without individual cards. Profile's decorative cuisine/frequency/goal emoji are omitted; shared callers keep their current presentation.
- Keep a labelled48px age input in a compact row. Reuse the translated autosave helper and move existing loading/saving/incomplete/error/retry states below the header so they remain findable while the form scrolls. Preserve complete-record save ordering and retries.
- Use h-dvh/min-h-0 with a bounded native hidden-scrollbar reader and89px plus safe-area navigation clearance. Preserve Profile main, other subviews and other pages.
- Verification:58 existing targeted tests, scoped lint/build pass; detector JSON[]. Desktop1280x900 keeps430px shell; Thai390x844 and English320x568 have no horizontal overflow, clear group rhythm,44px controls,16px custom inputs and reachable last goal. The single correction batch adjusted native-fieldset legend spacing and kept the selected border during hover. Synthetic load/save failure retry, classification, custom blur and goal selection pass; final console errors[]. No new presentation tests or full-suite/live backend/account/physical-device run. Evidence: tmp/profile-preferences-20261020/.

## Earlier main refinement

Mode: Operate. This refinement covers the main Profile landing view. Keep the existing HomeMade orange/white, self-hosted Thai font and centered430px shell. Language, history, help, preferences and editor retain their existing presentation and behavior.

- Task path: identity (avatar, display name, email, Edit), history, settings (language/preferences/help), then logout. The name/email wrap rather than truncate. No new user claims, account statistics, assets or copy.
- Structure:56px logo and44px Back/notification controls;80px avatar on white with the existing fallback. Edit belongs beside the identity. Use64px plain menu rows and dividers with flat orange icons. Per the user's follow-up, Logout retains a prominent full-width red background, white bold text and icon, pill shape and soft shadow. The compact Header option is used only by main; default Header stays unchanged for subviews.
- Scrolling: bounded native main reader with hidden scrollbar,24px end padding and89px+safe-area navigation clearance. Long names/email, retries and errors remain in the same scroll flow. Keep focus and selection in the existing dark-orange palette.
- Preserve auth/logout safeguards and navigation, avatar loading/cancellation/retry, saved notices, notification count/callback, edit/language/preferences/history/help and Cooking callbacks. Add alert semantics to the existing logout error; do not redesign the subviews or modify shared auth/editor components.
- Verification (2026-10-18): independent source assessment and parent browser/mechanical inspection;34 profile-language/history tests, scoped lint/build pass, detector JSON[]. Desktop1920px, Thai390px and English320×568 confirm wrapping without horizontal overflow, main bottom at nav top, no header-control collisions and reachable logout/error after scrolling. Synthetic checks cover edit/save notice, language change, history/preferences entry, avatar-error retry, logout failure retention and success routing to/login, notification and Cooking receipts. Receipts verify fixture callbacks, not the production router. No live account/backend mutation, physical device/avatar upload or full-suite certification.

Local proof: tmp/profile-20261018/thai-390-final.jpg, english-320-long.jpg and english-320-logout-error.jpg. No new motion or shipping raster assets.
