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

FIRST VIEWPORT: Item image and name lead into the inline form; Save/Cancel remain above the padded bottom navigation. Nutrition leads with status, then calories/macros, then a native disclosure. The compact shell remains centered on desktop.

FORM: Existing details and shared recipe section extended in code. No new identity choice or comp; seed key: incumbent-fridge-nutrition-20261013.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Base-menu extension (approved 2026-10-13)

Reuse this same layout and native disclosure for freshly calculated base-menu values. The status must distinguish database calculation with source limitations from an AI estimate; unavailable values must stay visibly absent. Details explain source/proxy/derived-value/constant limitations and raw-ingredient arithmetic, without claiming cooking-yield accuracy. Status and quantity basis still lead the first viewport. No new palette, font, token system, comp or shipping raster. Verification includes Thai390px limited, English320px unavailable and1280px calculated captures.
