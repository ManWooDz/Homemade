---
name: HomeMade
description: A warm, practical mobile kitchen companion that turns available ingredients into trustworthy cooking guidance.
colors:
  primary: "#ef5a3a"
  primary-soft: "#fdece5"
  canvas: "#ffffff"
  surface-subtle: "#f9fafb"
  ink: "#111827"
  text-muted: "#6b7280"
  text-secondary: "#374151"
  border: "#d1d5db"
  border-strong: "#9ca3af"
  nutrition-calorie: "#fff6f2"
  nutrition-carbs: "#e4fbec"
  nutrition-protein: "#eaf3ff"
  nutrition-fat: "#fffad8"
typography:
  display:
    fontFamily: '"Noto Sans Thai", "Leelawadee UI", Tahoma, sans-serif'
    fontSize: "2.125rem"
    fontWeight: 900
    lineHeight: 1
    letterSpacing: "normal"
  headline:
    fontFamily: '"Noto Sans Thai", "Leelawadee UI", Tahoma, sans-serif'
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.333
    letterSpacing: "normal"
  title:
    fontFamily: '"Noto Sans Thai", "Leelawadee UI", Tahoma, sans-serif'
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "normal"
  body:
    fontFamily: '"Noto Sans Thai", "Leelawadee UI", Tahoma, sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.65
    letterSpacing: "normal"
  body-large:
    fontFamily: '"Noto Sans Thai", "Leelawadee UI", Tahoma, sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.75
    letterSpacing: "normal"
  body-medium:
    fontFamily: '"Noto Sans Thai", "Leelawadee UI", Tahoma, sans-serif'
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.65
    letterSpacing: "normal"
  label:
    fontFamily: '"Noto Sans Thai", "Leelawadee UI", Tahoma, sans-serif'
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.65
    letterSpacing: "normal"
  caption:
    fontFamily: '"Noto Sans Thai", "Leelawadee UI", Tahoma, sans-serif'
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
rounded:
  small: "8px"
  control: "12px"
  information: "16px"
  card: "24px"
  pill: "9999px"
  sheet: "40px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "20px"
  "6": "24px"
  "8": "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.canvas}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 20px"
    height: "44px"
  button-icon:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.pill}"
    size: "56px"
  input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-large}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "44px"
  chip-selected:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.canvas}"
    typography: "{typography.body-large}"
    rounded: "{rounded.pill}"
    padding: "0 20px"
    height: "44px"
  card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "12px"
---

# Design System: HomeMade

CreateRecipe selected ingredients (2026-10-20): display only the first ingredient letter uppercase in both selected chips and the adjacent fridge list; retain original data and remaining capitalization. Distinguish the44px remove control with a centered28px dark-orange/white hover circle and darker active state, preserving its accessible name and44px focus outline. Details: .impeccable/surfaces/frontend-src-pages-createrecipe-jsx.md.

CustomCooking choice consistency (2026-10-20): retain the existing OptionChips in all four preference groups and their standard centered wrapping rows; remove the page-specific full-width/left-alignment override. Taste hint spacing and rounded Other input match CreateRecipe. Keep the existing dark-orange selected state and selection rules. Details: .impeccable/surfaces/preference-choices.md.

CreateRecipe choice consistency (2026-10-20): Taste now uses the same OptionChips as allergies, dietary preferences and equipment, with matching16px labels,44px minimum targets,8x20px padding, centered wrapping rows and consistent legend/hint rhythm. Use the existing #b93e25 selected background/border with white labels inside create-recipe-preferences only. Taste stays single-select with explicit existing guidance; other groups retain their multiple-choice rules. No shared-control or other-page styling change. Details: .impeccable/surfaces/frontend-src-pages-createrecipe-jsx.md.

Profile preference editor refinement (2026-10-20): align compact44px choices with their headings, use blush/dark-orange selections and24px section separators, and remove decorative emoji from this subview only. A compact labelled age row leads; the existing autosave/loading/error/retry copy stays visible beneath the header. Bound the hidden-scrollbar reader above navigation with safe-area clearance. These rules are scoped by profile-preferences-screen; shared choice components, other pages, Profile main, data and save behavior retain their existing contracts. Details: .impeccable/surfaces/frontend-src-pages-profile-jsx.md.

Preference flow update (2026-10-20): Profile, Onboarding and both generation forms share separate allergy/dietary/equipment controls; the generation taste list includes Not spicy. Retain the existing shell/font/palette and OptionChips, use named fieldsets and labelled custom text, and expose legacy classification plus account-load/retry states. Only the Profile preference subview reserves compact-header title space and labels its 48px age field; Profile main remains as previously refined. Details: .impeccable/surfaces/preference-choices.md. The accepted functional scope supersedes the earlier statements about retaining old preference defaults/payload assembly; the public API shape remains unchanged.

CreateRecipe refinement (2026-10-18):80px recipe image and wrapping title/description/tags on white; distinct ingredient, taste, allergy, equipment and extra groups. Local44px chips/removal controls use the existing blush/dark-orange palette. The Generate action and single preflight alert stay in a footer above navigation; native hidden-scrollbar content is bounded above it. Keep the original state, defaults, payload and allergy checks authoritative. No new asset, animation, shared control or global token change. Details: .impeccable/surfaces/frontend-src-pages-createrecipe-jsx.md.

Profile main refinement (2026-10-18): identity is grouped on white with an80px avatar, wrapping name/email and an adjacent outlined Edit control. History and settings use64px flat rows with dividers; per the user's follow-up, logout uses a prominent red fill with white bold text/icon and a soft shadow. Main opts into the compact56px-logo header while subviews retain their original header. A native hidden-scrollbar reader ends above navigation with safe-area clearance. No auth, copy, shared editor, asset or global identity change. Details: .impeccable/surfaces/frontend-src-pages-profile-jsx.md.

AddIngredient refinement (2026-10-18): stock fields now lead before photo selection, with a64px preview beside the existing image-search heading. A persistent action/error footer sits between the native content scroller and bottom navigation. Controls use48px minimum heights,12px corners and the existing dark-orange action/focus colors; selected categories use the existing blush tint. All changes are scoped to this page. Existing copy, barcode/search/upload behavior and shared OFF nutrition remain authoritative. Details: .impeccable/surfaces/frontend-src-pages-addingredient-jsx.md.

IngredientDetail refinement (2026-10-18): the existing mobile shell now groups its96px circular photo with name/category, followed by a divided quantity/estimated-expiry list and the main Edit action. Optional Open Food Facts nutrition stays in its existing neutral panel below; deletion uses a quiet secondary action. The56px logo and bounded scroller improve usable space while retaining navigation clearance. Page-scoped primary buttons reuse #b93e25 for contrast; shared editor/nutrition components, product copy and data semantics are unchanged. No new assets or global identity change. Surface details and verification: .impeccable/surfaces/frontend-src-pages-ingredientdetail-jsx.md.

## Overview

### Provenance and Authority

The current HomeMade UI was designed in Figma by another member of the project team. The token values, component patterns, layout behavior, shadows, motion, and responsive constraints recorded here were extracted from the current implementation on 2026-10-06. They are a descriptive snapshot of what is implemented, not a redesign brief and not proof of the original designer's intent.

The original Figma file was not inspected during this documentation pass; the Figma provenance above is team-provided context.

The user-approved Thai copy and typography refinement on 2026-10-13 updates only the font family, semantic type roles and navigation captions below from the shipped implementation. Other design records retain the 2026-10-06 snapshot; unrelated drift is recorded in `docs/thai-copy-typography-review-2026-10-13.md` rather than resolved by this typography pass.

The Creative North Star, mood language, descriptive color names, named rules, and design philosophy in this document are working qualitative language created during documentation. They remain pending confirmation by the original Figma designer and must not be attributed to that designer until confirmed.

If Figma and the implementation disagree, neither source wins automatically. Report the exact difference and ask the team before choosing a source of truth, changing this documentation, changing Figma, or changing application code.

**Creative North Star: "The Friendly Kitchen Counter"** — working qualitative language pending confirmation by the original Figma designer.

As working qualitative language, HomeMade is described as a clean, welcoming kitchen counter where the next useful action is always within reach. The world is warm, cheerful, and easy to use, expressed through a white canvas, HomeMade Orange actions, generous breathing room, friendly rounded forms, and direct Thai-first language.

The current working philosophy uses restraint to communicate trust rather than clinical styling. Nutrition, allergen, and safety information uses calmer hierarchy, explicit labels, moderate corners, and limited semantic color so factual content feels clear and dependable without turning the product into a medical dashboard. The system should not feel luxurious, premium-restaurant-like, visually crowded, or childlike.

**Key Characteristics:**
- Mobile-first and task-focused within a narrow app shell.
- Warm white surfaces with one energetic general-purpose accent.
- Soft, confident controls and large friendly cards.
- Selective light elevation for genuinely raised layers.
- Restrained factual styling for nutrition, allergens, and warnings.

## Colors

The palette is warm and sparse: HomeMade Orange carries action and identity, cool neutrals carry structure, and pastel color is reserved for nutrition data.

The values and role mappings below are extracted from the implementation. Names such as “HomeMade Orange,” “Soft Apricot,” and the nutrition-pastel names are working descriptive labels pending confirmation by the original Figma designer.

### Primary
- **HomeMade Orange** (`colors.primary`): Primary actions, active filter chips, directional icon buttons, and small brand accents.
- **Soft Apricot** (`colors.primary-soft`): Selected choice rows and gentle brand-tinted feedback where a solid accent would be too strong.

### Neutral
- **Kitchen White** (`colors.canvas`): The dominant app surface and card background.
- **Counter Mist** (`colors.surface-subtle`): Recessed fields, quiet list rows, and secondary surface separation.
- **Kitchen Ink** (`colors.ink`): Primary headings and body text that must carry authority.
- **Muted Slate** (`colors.text-muted`): Supporting copy, placeholders, and inactive navigation labels.
- **Deep Slate** (`colors.text-secondary`): Secondary text that still needs strong readability.
- **Soft Steel** (`colors.border`): Standard field and container borders.
- **Strong Steel** (`colors.border-strong`): Unselected choice controls and stronger structural boundaries.

### Nutrition-only palette
- **Calorie Blush** (`colors.nutrition-calorie`): Calorie summary surface.
- **Carbohydrate Mint** (`colors.nutrition-carbs`): Carbohydrate macro tile only.
- **Protein Sky** (`colors.nutrition-protein`): Protein macro tile only.
- **Fat Custard** (`colors.nutrition-fat`): Fat macro tile only.

**The One Accent Rule.** HomeMade Orange is the only general-purpose accent. Nutrition pastels stay inside nutrition displays, and safety colors stay inside status or warning contexts.

## Typography

**Display Font:** Noto Sans Thai with Leelawadee UI, Tahoma and sans-serif fallbacks

**Body Font:** Noto Sans Thai with the same fallbacks

**Label Font:** Noto Sans Thai with the same fallbacks

**Character:** The user-approved refinement uses one readable Thai/Latin family with room for Thai marks and short, practical Thai phrasing. Warmth still comes from weight, spacing and the existing hand-drawn logo. The broader qualitative interpretation remains pending confirmation by the original Figma designer.

Normal variable weights 400–900 are self-hosted as Thai, Latin and Latin-extended WOFF2 subsets with Unicode ranges and `font-display: swap`. The three font files total 73,616 bytes; their SIL Open Font License is retained beside them. The app makes no runtime Google Fonts request. The body inherits the family and the body role's line height; semantic reading roles below override that spacing where used. Existing utility sizes and explicit leading remain local variants.

### Hierarchy
- **Display** (900, 34px, 1.0): Rare promotional emphasis inside imagery; may be italic when the existing banner treatment calls for it.
- **Headline** (700, 24px, 1.333): Main page and recipe titles.
- **Title** (`typography.title`): The semantic h2 role for section headings and important factual groups; existing uses choose semibold or bold weight.
- **Body** (`typography.body`): Default page text and controls inheriting body spacing.
- **Body large** (`typography.body-large`): Semantic reading text, auth inputs and choice options with extra Thai line spacing.
- **Body medium** (`typography.body-medium`): Semantic supporting text and compact options.
- **Label** (`typography.label`): The semibold body-medium role for form actions and labels.
- **Caption** (`typography.caption`): Semantic helper text and navigation captions. Bottom-navigation captions override the regular role with semibold weight (600).

**The Plain-Language Type Rule.** Use one Noto Sans Thai family with the established Thai-capable fallbacks, and create hierarchy with size, weight and line spacing; do not introduce ornamental display faces.

## Layout

HomeMade is an Operate-mode interface built as a centered mobile workspace. The app shell fills the viewport, stays at or below 430px wide, and sits on a quiet gray surround on larger screens. It does not fan out into a desktop dashboard.

Page content normally uses 20–24px horizontal padding; auth and focused form screens may use 24–32px. The recurring rhythm is 8px for tight relationships, 12–16px within components, 20–24px between sections, and 32px for major separation. Headers keep the logo or title centered, while primary navigation stays anchored to the bottom with enough content padding to avoid overlap.

Recipe and favorite cards use a two-column grid with a 16px gap. Nutrition macros use a three-column grid with a 12px gap. Filters and chips may scroll horizontally rather than compressing labels or adding desktop-only density.

## Elevation & Depth

The system is layered but light. Most controls and information blocks rely on fill, border, and spacing. Small and medium shadows identify tappable cards or floating controls; stronger upward shadows belong to bottom navigation and sheets. The large app-shell shadow exists mainly to frame the mobile canvas on wider screens.

### Shadow Vocabulary
- **Quiet card** (`0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)`): Recipe cards and lightly lifted information tiles.
- **Floating control** (`0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)`): Circular direction buttons and emphasized actions.
- **Raised sheet** (`0 -10px 40px rgb(0 0 0 / 0.1)`): Bottom navigation, filters, and draggable sheets.
- **Desktop frame** (`0 25px 50px -12px rgb(0 0 0 / 0.25)`): The 430px app shell when it sits inside a wider viewport.

**The Lift What Moves Rule.** Resting content stays flat or lightly raised. Stronger shadows are reserved for the app shell, floating controls, navigation, and sheets.

## Shapes

The form language is rounded but role-aware. Buttons, inputs, and chips use capsule silhouettes to feel comfortable and immediately tappable. Cards use large 24px corners for warmth. Factual information, nutrition notes, and safety warnings use moderate 16px corners so they remain friendly without losing structure. Bottom sheets use 24–40px top corners to make their separate layer obvious.

Avoid applying the capsule silhouette to dense information containers, warnings, recipe cards, or full panels. Small 8–12px corners are reserved for compact controls such as OTP fields, camera frames, and tightly bounded widgets.

## Components

The component language is **soft and confident**: friendly curvature and comfortable targets, paired with unmistakable action hierarchy.

### Buttons
- **Shape:** Full capsule for text actions; circular capsule for directional or icon-only actions.
- **Primary:** HomeMade Orange with white text, 44px height, 14px semibold label, and 20px horizontal padding. Full-width form actions use the same height and treatment.
- **Hover / Focus:** Slight opacity or darker-orange shift over a 150ms standard transition. Keyboard focus must remain visible; form controls use an orange border and restrained orange ring.
- **Secondary / Ghost:** White or subtle-neutral surface with a gray or orange border. Destructive actions use red only for the destructive context.

### Chips
- **Style:** 44px capsule with 20px horizontal padding. Unselected chips use a white surface, strong-steel border, and deep-slate text.
- **State:** Selected chips use HomeMade Orange with white text. A softer apricot selected state is acceptable for list-style choices where a filled orange row would dominate.

### Cards / Containers
- **Corner Style:** Large friendly corners (24px) for recipe and feature cards.
- **Background:** Kitchen White or Counter Mist, with nutrition pastels restricted to macro summaries.
- **Shadow Strategy:** Quiet-card shadow only when the card is tappable or needs separation from the canvas.
- **Border:** Very light neutral border for white cards; no decorative multicolor borders.
- **Internal Padding:** 12–20px according to content density.

### Inputs / Fields
- **Style:** White 44px capsule with a soft-steel border, 16px body text, and 16px horizontal padding.
- **Focus:** HomeMade Orange border; complex generation fields may add a restrained translucent orange ring.
- **Error / Disabled:** Errors use concise red text near the field. Disabled actions reduce opacity without changing their structural size.

### Navigation
- **Style:** White bottom navigation with a thin neutral top border, 24px top corners, and a restrained upward shadow. Labels use the caption role at semibold weight (600); inactive items are muted slate and active items use the brand accent.
- **Primary action:** Cooking is the raised central circular action, visually separated from the four standard destinations.

### Nutrition Summary
- **Style:** Calories receive a wide blush summary card; carbohydrates, protein, and fat use three equal pastel tiles. Numeric values lead with 24–36px weight; labels remain neutral and compact.
- **Boundary:** Pastel tiles communicate nutrition categories only. They are not a general dashboard palette.

### Safety and Allergen Notices
- **Style:** Moderate 16px corners, explicit icon and label, semantic border, and restrained tinted background.
- **Tone:** Clear and matter-of-fact. Do not add dramatic shadows, playful decoration, or clinical dashboard chrome.

## Do's and Don'ts

These are working guardrails for using the implementation snapshot consistently. They are not claims about the original Figma designer's intent and remain subject to team confirmation.

### Do:
- **Do** use HomeMade Orange to identify primary actions, active filters, and directional icon buttons.
- **Do** keep important nutrition and allergen information explicit, readable, and visually calmer than promotional content.
- **Do** reserve pastel macro colors for nutrition summaries.
- **Do** use 8–24px spacing steps and large empty areas to keep narrow screens scannable.
- **Do** use shadows only when an element genuinely sits above another layer.

### Don't:
- **Don't** style HomeMade like a premium restaurant, a clinical health product, or a children's app.
- **Don't** introduce additional general-purpose accent colors or multicolor decoration.
- **Don't** apply capsule shapes to cards, warnings, or dense information blocks.
- **Don't** stretch the interface past the 430px mobile shell or convert it into a dense desktop dashboard.
- **Don't** give factual warnings promotional styling or make them compete visually with the primary task.
