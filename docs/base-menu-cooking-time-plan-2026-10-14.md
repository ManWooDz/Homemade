# Base-menu estimated recipe time — review proposal

Status: user approved all ranges and the implementation/live activation scope, 2026-10-14 Bangkok. Implemented, activated in the current dev DB and verified; user subsequently requested scoped commit/push.

Final evidence: 49 relevant offline backend checks (guard violations zero), 19 frontend checks, production build and three actual-app browser captures pass. Live API exposes nine approved ranges; private backup/activation/browser receipts and screenshots are in `tmp/base-menu-time-20261014/`. The final read-only DB snapshot equals the verified activation after-state. Existing `motion` lint error reproduced on HEAD; existing bundle-size warning retained. No measured cooking trial or full-suite claim. Source model changes were made after the additive live migration to keep the running app compatible during activation.

Scoped source delivery verification: clean parent HEAD plus only this feature passes42offline backend checks (guard0),11frontend checks and production build2226modules. Nutrition/fridge/typography WIP and private backups are excluded from the source delivery. Standalone regression files keep the commit independent of pending nutrition code.

## Accepted meaning and scope

Only the base menus displayed by RecipeDetail. Use a reviewed approximate range of total elapsed time including preparation, cooking and waiting in the current instructions. Prepared foods start prepared: Chashu Ramen uses ready broth/chashu/egg; Rainbow Healthy uses ready-to-eat edamame because its procedure contains no edamame-cooking step. No measured-time or source-certified claim. No new academic KPI; this is product envelope.

## Proposed ranges for review

These are project estimates from the existing procedures, not published source values or results of timed cooking trials.

| Current catalog name | Minutes | Basis/assumption |
| --- | --- | --- |
| Superfood Veggie | 25–35 | Includes cooking quinoa, preparing vegetables and assembling; package timing can vary. |
| Fresh Power Salad | 10–15 | Wash, dry, cut and dress; dressing is prepared. |
| Rainbow Healthy | 15–20 | Cut and assemble; edamame and dressing are prepared. |
| Chashu Ramen | 15–20 | Heat prepared broth/chashu, boil noodles and assemble with prepared egg. |
| Padthai with shrimps | 30–45 | Includes noodle soaking, sauce mixing, preparation and stir-frying; noodle package timing can vary. |
| Stir-Fried Basil with pork | 15–25 | Prepare/pound aromatics and stir-fry; minced pork is ready to use; no rice-cooking step. |
| Greek Salad | 10–15 | Cut, assemble and dress. |
| Grilled Steak | 20–30 | Prepare, heat pan, sear/baste and rest five minutes; steak thickness/doneness can vary. |
| Tom Yum Kung | 25–35 | Prepare shrimp/herbs/vegetables and cook/season soup. |

No extra waiting such as shopping, thawing or preparing the named prepared foods is counted unless the current recipe specifies that step. No automatic multiplication by servings or inference from number of steps.

## Exact proposed implementation scope

Backend edits require the user's separate confirmation before any edit:

1. `backend/database/models.py`: add nullable integer `total_time_min_minutes` / `total_time_max_minutes` to BaseRecipe. Require either both null or both positive integers with min <= max via a table constraint shared with the migration. Legacy/new unmatched menus keep null.
2. `backend/alembic/versions/a8b9c0d1e2f3_base_recipe_cooking_time.py`: additive migration after observed source head `f7a8b9c0d1e2`; add those columns/constraint and guarded backfill of only the proposed nine ranges. Use migration-local snapshot values, not imports of the seed/runtime. Match expected catalog name, ingredients, instructions and servings before filling previously empty time fields. Changed/unmatched rows keep null and are reported during activation. Re-running seed is not part of activation.
3. `backend/database/seed_postgres.py`: add the proposed minute ranges to the nine seed recipes, preserve its existing behavior for other fields; add time-only assignments to its existing update path. This supports future seeded environments, but full seed will not run against the current DB for this feature.
4. `backend/main.py`: GET `/api/recipes` adds `estimated_total_time: {min_minutes: int, max_minutes: int}` or null, sourced only from the stored base-menu range. Preserve existing response fields/nutrition logic; GET does not write. Generated recipe endpoints/prompts/history stay outside scope.
5. `backend/tests/test_seed_postgres_nutrition.py`: cover valid complete ranges for all nine seed menus, persistence on create/update and preservation of unrelated seed behavior using in-memory SQLite.
6. `backend/tests/test_base_recipe_time.py`: standalone valid/null time, DB range constraint and read-only GET regressions. Delivery uses a standalone test to avoid depending on unrelated pending nutrition work; no live DB/provider needed. Existing nutrition tests remain local.

Frontend/documentation scope:

- `frontend/src/pages/RecipeDetail.jsx`: display `ประมาณ 20–30 นาที` / `About 20–30 min` for valid ranges, and a neutral missing-time label for null/invalid ranges. Show a concise translated explanation that time includes preparation/cooking/waiting according to the recipe and assumes named prepared foods are ready. This field does not use the generated recipe `usage_time` placeholder.
- `frontend/src/utils/translations.js`: add only the copy used by this feature.
- `frontend/test/recipeTiming.test.js`: use the actual RecipeDetail SSR harness for both locales, valid range, missing/invalid range and review spacing. Standalone delivery avoids pending nutrition component/test dependencies; existing nutrition tests remain local.
- `docs/data-contracts/base-menu-cooking-time.md`: additive field, units, validity, null semantics and estimate meaning; `spec.md` records completed checks and activation outcome. Accepted vocabulary is already in GLOSSARY.md.

## Verification and current-application activation

After approval, run the relevant offline backend tests with existing runtime/dependencies and synthetic config/in-memory DB, frontend SSR tests, production build and scoped whitespace check. Add no packages. Preserve existing unrelated WIP.

To make the feature visible in the current application, the same proposed scope includes checking the actual configured local DB/container/volume and current migration revision, saving/verifying a backup and before-state, then applying only this additive migration/backfill. If live revision/schema differs from the reviewed source prerequisites, stop and report before writes; do not run unrelated pending migrations. Verify all existing non-time fields and other tables remain unchanged, check all nine ranges/null exceptions, GET output and actual RecipeDetail UI. No full reseed, nutrition rewrite or provider call.

## Concerns and reversal

- Source-only inspection has not verified the actual DB revision or current row inputs. Backfill must not assign the proposed ranges to changed recipes merely because their names match.
- Time ranges can be optimistic for beginners, different equipment or steak thickness. Keep approximate wording and ingredient-state assumptions visible; calibrate by timed trials later.
- Blast radius: BaseRecipe SELECTs need the new columns, so apply the approved additive migration before activating new ORM code/restarting the backend. Other endpoints and existing DB rows retain their data.
- If reversal is needed, restore the previous application code while retaining the additive columns; do not automatically drop columns or run a destructive downgrade. Saved old time values support a separately reviewed time-only reversal if necessary.
- No ADR: these are ordinary additive display fields without a surprising architectural trade-off.
