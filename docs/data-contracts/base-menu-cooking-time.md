# Base-menu cooking-time contract

Approved 2026-10-14 Bangkok. Product envelope; only base menus on RecipeDetail.

GET `/api/recipes` adds `estimated_total_time` to each menu:

```json
{"estimated_total_time": {"min_minutes": 15, "max_minutes": 20}}
```

Both values are positive integer minutes with `max_minutes >= min_minutes`. When the range is not known, the field is null; null is not zero. Existing response fields are unchanged. GET reads stored time fields and never writes. BaseRecipe stores nullable integer `total_time_min_minutes` / `total_time_max_minutes` with an all-null-or-valid-pair database check.

The range estimates elapsed preparation, cooking and waiting in the current recipe, from recipe-ready ingredients until food is ready to eat. Named prepared foods start prepared: Ramen assumes prepared broth/chashu/egg and Rainbow Healthy assumes ready-to-eat edamame. No shopping, thawing, rice cooking or preparing those prepared foods is counted unless specified by that recipe. Values were project-estimated and user-reviewed, not timed experimentally or source-certified; they are not guarantees and do not automatically scale with servings.

RecipeDetail displays `ประมาณ 15–20 นาที` / `About 15–20 min` and visible translated ingredient-state/time-boundary help. It rejects incomplete, non-integer, nonpositive or reversed ranges and displays `ยังไม่มีข้อมูลเวลา` / `Time unavailable`. It does not derive a time from `usage_time`, step count or nutrition.

The approved ranges are in `docs/base-menu-cooking-time-plan-2026-10-14.md`. Migration `a8b9c0d1e2f3` follows `f7a8b9c0d1e2` and fills only empty times whose names and pinned ingredients/instructions/servings match the reviewed recipes. Changed/unmatched menus remain unknown. Migration snapshots are independent of the mutable seed/runtime. Future seed runs create ranges and fill matching empty ranges without replacing an existing reviewed range; the seed retains its preexisting other-field behavior and is not a time-only maintenance tool.

Deployment order: apply the additive migration before activating the new BaseRecipe ORM. Rollback uses previous application code with additive columns retained; destructive column drops are not automatic. Generated recipe schemas, prompts, CookingPage/RecipeContent and saved history are outside this change.

Local dev activation was applied and verified on 2026-10-14: nine time pairs filled; original recipe fields, all fourteen other non-revision tables and sequences unchanged. `alembic_version` advances to `a8b9c0d1e2f3`. Private backup/pre/post fingerprints and receipts are retained under `tmp/base-menu-time-20261014/`; do not publish the database dump or SQL read-back.
