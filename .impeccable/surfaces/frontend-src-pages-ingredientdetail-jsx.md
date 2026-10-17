---
version: 1
slug: "frontend-src-pages-ingredientdetail-jsx"
primary_target: "frontend/src/pages/IngredientDetail.jsx"
related_targets: ["frontend/src/components/IngredientEditor.jsx","frontend/src/components/RecipeNutrition.jsx","frontend/src/components/RecipeContent.jsx","frontend/src/pages/RecipeDetail.jsx"]
---

# Fridge and recipe nutrition extension

Mode: Operate. Keep the existing orange/white, self-hosted Noto Sans Thai and 430px mobile shell. The user approved the scoped backend update plan on 2026-10-13. This is an extension of established screens, without a new visual world or raster assets.

## Direction contract

THESIS: Make uncertainty inspectable and one fridge item editable without leaving its details.

OWN-WORLD: Existing capsule inputs/actions, calm neutral information panels, blush calorie block and three nutrition pastel tiles. Clear labels and visible keyboard focus in Thai and English.

STORY: Users see the nutrition status and quantity basis first; expand to compare existing calculated and AI values. They edit the inventory through explicit Save/Cancel and keep their draft on save failure.

FIRST VIEWPORT: IngredientDetail has a compact image/name/category identity, then a divided inventory definition list (quantity and estimated expiry), then the main Edit action. Optional Open Food Facts nutrition remains separate below, with its source/basis and missing values intact; deletion is a quiet secondary action. The inline editor keeps its existing fields, validation and Save/Cancel. A bounded native scroller ends above navigation, including safe-area clearance. The compact shell remains centered on desktop. Shared recipe nutrition elsewhere retains its existing status/disclosure.

FORM: Existing details and shared recipe section extended in code. No new identity choice or comp; seed key: incumbent-fridge-nutrition-20261013.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Base-menu extension (approved 2026-10-13)

Reuse this same layout and native disclosure for freshly calculated base-menu values. The status must distinguish database calculation with source limitations from an AI estimate; unavailable values must stay visibly absent. Details explain source/proxy/derived-value/constant limitations and raw-ingredient arithmetic, without claiming cooking-yield accuracy. Status and quantity basis still lead the first viewport. No new palette, font, token system, comp or shipping raster. Verification includes Thai390px limited, English320px unavailable and1280px calculated captures.

## IngredientDetail refinement (2026-10-18)

- Preserve the existing orange/white identity, photo, copy, data, API calls and inventory workflows. Reduce the logo to56px and the item photo to96px, align name/category alongside it, and use proximity/dividers rather than separate cards for inventory values. Give expiry notices their own line and retain the estimate qualifier. The primary action uses the established accessible dark orange; delete is a44px quiet text action. All page styles are scoped; NutritionBox and IngredientEditor are unchanged.
- Independent source layout assessment plus parent browser/mechanical assessment informed the direction. Final detector JSON[]; scoped lint/build pass. Browser evidence covers desktop, Thai390px and English320px/568px with long names, missing stock data, partial OFF values, synthetic successful/failed saves, cancel focus return and nav callback. No horizontal overflow; main bottom equals nav top, and editor Save/delete remain reachable above nav. No new shipping raster or animation.
- Targeted existing tests:13/14 pass; the unchanged ingredientPayload test's legacy expected object omits the helper's existing null metadata fields. Both test/helper are identical to HEAD. No full-suite, physical-device, real deletion or live-account/backend mutation check. Synthetic QA captures live locally under tmp/ingredient-detail-20261018/.
