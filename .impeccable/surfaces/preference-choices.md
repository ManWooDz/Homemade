---
version: 1
slug: "preference-choices"
primary_target: "frontend/src/components/CookingPreferenceFields.jsx"
related_targets: ["frontend/src/pages/Profile.jsx", "frontend/src/pages/auth/Onboarding.jsx", "frontend/src/pages/CreateRecipe.jsx", "frontend/src/pages/CustomCookingPage.jsx"]
---

# Cooking preferences

Mode: Operate. Extend the existing HomeMade orange/white, Thai-font, 430px mobile shell with the user-confirmed shared choices and account defaults. Preserve surrounding ingredient, navigation, Profile main and six-step Onboarding behavior.

Profile-specific refinement (2026-10-20): the preference editor now overrides the shared presentation with left-aligned compact choices, blush selections and24px section separators, plus header-level existing save/error feedback. Other callers retain the shared32px group spacing. See frontend-src-pages-profile-jsx.md for its scoped visual evidence; data/category behavior below is unchanged.

CustomCooking refinement (2026-10-20): all four groups already used OptionChips. Removed its page-specific full-width/left-alignment override to restore standard centered wrapping rows; Taste hint spacing and rounded Other input now match CreateRecipe. Keep the existing dark-orange selected state and all selection/default/request behavior.28 targeted tests, scoped lint/build and detector pass; synthetic browser checks confirm single Taste, multiple allergies and custom Taste request values. Thai390x844, English320x568 and desktop1280x900 have no horizontal overflow; all groups use16px labels,8x20px padding and45.6px targets. Console errors[]. Evidence: tmp/custom-cooking-choices-20261020/. No live-account/backend/provider or physical-device check.

- Separate named allergy, dietary and equipment fieldsets with 32px group spacing, wrapping existing OptionChips, 44px minimum choices, palette focus outlines and labelled 16px custom textareas. No allergy can coexist with Vegan; each None is exclusive only in its group. Shared taste choices stay in generation forms.
- Legacy unclassified text appears intact above the groups with native category selects; generation remains blocked until classified. Category-specific Other text remains visible and editable after blur/reload, including multiple entries.
- Generation loading/error/retry and clarification messages remain beside the persistent Generate action. Profile exposes loading, saving and save/load retry states. Scope the compact header to the preference subview to reserve space between the Back control and long Thai title; give the age input a native label and 48px minimum height.
- No new asset, animation, package or global visual token. The original Profile main and CreateRecipe design records describe their earlier refinements; this record supersedes only their preference-control/default-fill preservation statements for the newly approved scope.

Verification (2026-10-20): bounded inspection and one correction batch reserved Profile's Back/title space and removed fixture navigation from final captures. Actual desktop982px retains the430px shell; Thai390x844 and English320x568 show no horizontal overflow. Fresh-tab console errors are empty. Synthetic browser flows cover six-step Onboarding persistence, Profile custom blur/reopening, generation-only overrides, legacy classification, failed-load retry, empty accounts and deliberately cleared fields during delayed loading. Focused tests32/32 pass; full suite158/162 retains four documented unrelated failures; scoped lint/build and detector pass with the existing bundle warning. See tmp/preference-choices-20261020/ and the current spec for exact limits. No real account/backend/provider or physical-device verification.
