---
version: 1
slug: "frontend-src-components-recipegenerating-jsx"
primary_target: "frontend/src/components/RecipeGenerating.jsx"
related_targets: ["frontend/src/pages/CookingPage.jsx"]
---

# Recipe generation wait

Mode: Operate. Preserve the warm, simple white/orange HomeMade mobile shell, existing generation copy, font and logo. User requests rotating sentences with matching icons while waiting.

- Keep a stable generation heading and explanation; four recipe notes and Lucide icons rotate together every 3.5 seconds (user follow-up2026-10-23). Notes explain ingredients, preferences, cooking steps and review, not live pipeline milestones. No percentages, completion ticks, time estimates or medical guarantees.
- Use a muted blush 144px circle, dark orange icon/text, gentle note entrance and small waiting dots. Respect reduced motion. Keep one stable accessible status; rotating explanatory notes do not repeatedly interrupt screen readers.
- Keep the 430px shell and 72px logo. Allow the main area to scroll on short/zoomed screens, with stable space for localized notes. Timer is owned by the mounted waiting component and cleaned up on exit. Both generation paths use it through CookingPage.
- No backend, API, package, account or recipe-output changes. This is product-envelope UI.

Verification receipts and screenshots: `tmp/recipe-loading-20261023/`. Physical-phone and real-provider checks are separate from the synthetic preview.

Verified2026-10-23:44focused tests, scoped ESLint and production build pass; detector[] during pass. Browser320px Thai/English,430px Thai and1280px English show no overflow or required inner scrolling, one stable status and empty console errors. Note/icon changes observed; unit check covers all four pairs, wrap and cleanup. Compact short-screen layout retains readable body text. Existing two source-location contract assertions fail against both before/after; no unrelated test rewrite. Existing bundle warning and design-sidecar staleness retained.
