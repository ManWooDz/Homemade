---
version: 1
slug: "frontend-src-pages-addingredient-jsx"
primary_target: "frontend/src/pages/AddIngredient.jsx"
related_targets: ["frontend/src/components/NutritionBox.jsx", "frontend/src/pages/IngredientDetail.jsx"]
---

# Add Ingredient

Mode: Operate. Preserve the existing HomeMade orange/white identity, self-hosted Thai font and centered430px shell. This is an inventory-entry refinement, not a new visual world.

- Reading/task path: title, name, category, optional quantity/unit, optional estimated expiry, image preview/search/upload and any scanned OFF nutrition. Keep every existing field and factual label. Photography supports inventory entry rather than occupying the first viewport.
- Structure: match IngredientDetail's56px logo/44px Back control, use48px inputs and quiet selected-category styling. Keep the image search open and native, with its64px selected preview beside the heading. Separate it from stock fields by proximity and a single divider, without adding cards or a modal. Pair amount/unit in equal min-width-zero grid columns.
- Action: a non-overlapping footer remains above the existing bottom navigation and safe area. It contains the existing Add to My Fridge action plus announced save errors. The scrollable content ends at that footer, and the footer ends at navigation. Native field labels, category/photo pressed states, numbered photo names and page-scoped focus/selection/caret styling support keyboard use.
- Truth/behavior: preserve defaults, debounced name/search lookup, upload/camera input, barcode name/category/photo/nutrition prefill, selected-image state, quantity validation, optional-null payloads, sorting and callbacks. NutritionBox remains unchanged. Do not add nutrition claims or convert the OFF values into engine calculations.
- Verification (2026-10-18): independent source assessment and parent visual/mechanical inspection; detector JSON[], scoped lint and production build pass. Desktop1920px/Thai390px/English320×568 verify no horizontal overflow, reachable save above nav in normal/error states, manual selection and barcode payload preservation, invalid quantity rejection and failed-save draft retention. Existing targeted tests13/14 pass with the unchanged legacy null-metadata expectation failing. No live inventory mutation, physical camera/upload/device, full-suite or successful native date-entry automation check. Synthetic receipts do not prove App navigation.

Local visual evidence: tmp/add-ingredient-20261018/thai-390.jpg and english-320-save-error.jpg. No new shipping imagery, packages or animation; existing search/upload spinners remain.
