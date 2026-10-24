# Recipe generation protocol and Gemini key routing

Current production Gemini, benchmark Gemini and local generation share a closed
instruction schema in `backend/recipe_instructions.py`. HTTP recipes and saved
history still expose Thai instruction strings. No database migration is needed.

## Model instructions

The backend builds a request-specific registry of canonical selected ingredients
and permitted pantry ingredients. The model uses only those IDs in action objects;
the backend validates references and renders Thai sentences. This avoids scanning
rendered phrases such as คลุกเคล้า for unrelated ingredient substrings such as เคล.

Each step requires `action`, `ingredients`, `targets` and `excluded`. Optional
`minutes` and `temperature_c` must be positive finite numbers when provided.
`adjusted_ingredients` uses a permitted name followed by its quantity, without IDs.
Existing range/fraction/vague-quantity parsing remains independent of admission.

| Actions | ingredients | targets |
| --- | --- | --- |
| Preparation/cooking methods | Food used; nonempty in generation schema | Empty |
| add, season | Additions or seasonings; nonempty | Receiving food; nonempty |
| serve, serve_separately | Optional garnish/accompaniment | Main food; nonempty |
| rest, drain, set_aside | Exactly one positive role | Exactly one positive role |

The schema uses four `anyOf` shapes. All IDs must be known, positive references
must be declared, and IDs cannot overlap between roles or be duplicated. The model
cannot add free-text fields, invent IDs or select a legacy protocol. These checks
remain authoritative even when a provider ignores the generation schema.

For a registry with `i1=egg`, `i2=oil`, `i3=minced pork`, an explicit separate egg
component can be represented as follows (declarations are omitted from this step
illustration):

```json
[
  {"action":"fry","ingredients":["i1","i2"],"targets":[],"excluded":[]},
  {"action":"set_aside","ingredients":[],"targets":["i1"],"excluded":[]},
  {"action":"heat","ingredients":["i2"],"targets":[],"excluded":[]},
  {"action":"stir_fry","ingredients":["i3"],"targets":[],"excluded":[]},
  {"action":"serve","ingredients":["i1"],"targets":["i3"],"excluded":[]}
]
```

Reviewed oil identities render as a medium, for example ทอดไข่ในน้ำมันให้สุกทั่วถึง.
Their IDs and amounts remain in the plan for ingredient, allergy and nutrition
processing. `set_aside` renders ตัก…ขึ้นพักไว้ and does not count as cooking.

Optional `estimated_total_time` display metadata is retained as a positive integer
`min_minutes`/`max_minutes` range or `null`. Missing/malformed timing metadata alone
normalizes to unknown; it does not trigger another generation request. Timing
helper/contract tests are included because the current shared schema imports them.

## Validation and public output

Format/role normalization precedes Ingredient admission, Allergy, Flavor, Cooking
Logic, Nutrition sanity and Core checks. Cooking-quality checks stay after Allergy.
The existing generation feedback loop remains capped at three total attempts.
The reference-based Nutrition Engine runs after an accepted recipe; the model's
nutrition estimates and preliminary sanity checks do not establish grounded totals.

Cooking Logic requires an explicit cooking action for used minced pork, beef steak,
shrimp, egg and ไข่ไก่ before serving. Adding, beating, heating, a duration or a
temperature alone does not satisfy that rule. Reviewed oils are oil, vegetable oil
and olive oil. Oil-only frying is refused with guidance to use `heat` instead.

A bounded unnamed-pan check tracks explicit non-oil food IDs in fry/stir_fry/
dry_fry/water_saute. An oil-only `heat` starting another cycle requires previously
tracked food to be explicitly set aside or served. Explicit-food reheating and
direct sequential cooking remain allowed. Partial transfers remove only named IDs;
Flavor likewise retains unrelated food when a component is set aside.

Private `_instruction_plan`, `_instruction_protocol` and format-error metadata are
removed before public/history/Nutrition Engine output. Benchmarks retain a separate
plan/protocol audit and distinguish provider/format errors from hallucination
measurements. Historical prose training and stored Thai strings remain supported;
direct legacy normalization is for historical/offline callers, not a model fallback.

## Gemini keys and request bounds

`backend/gemini_keys.py` is shared by production generation, benchmark Gemini,
nutrition LLM fallback and embeddings:

- With both distinct keys configured, each operation first tries
  `GEMINI_API_KEY_FREE` and falls back once to `GEMINI_API_KEY` only on SDK HTTP 429.
- Authentication/server/timeout/schema/recipe failures do not switch keys. A later
  operation starts with the free key again; there is no permanent paid-key latch.
- SDK attempts are set to one. Explicit/injected clients bypass automatic routing;
  an explicitly empty key means no client. A single configured key is used directly.
- One routed operation may make two API calls, including one paid-key call. Three
  recipe attempts may therefore make six generation calls, including three paid-key
  calls; embedding/nutrition operations are additional. Key names do not establish
  the actual Google project's billing tier.

Keep both values in the existing ignored environment configuration. No credentials
or live request logs belong in Git. Restart the backend after changing its keys.
The offline runner clears both real keys and blocks external network/non-SQLite DB
access, including attempts to reload credentials through dotenv.

## Verification and limits

Regression tests cover declaration formatting, roles/schema, rendering, raw-food
cooking mentions, pan transitions, Allergy priority, Flavor separation, private
field stripping, provider wrappers, benchmark error accounting and key routing.
Run `python tests/run_offline.py` from `backend` using the configured project
environment. Windows asyncio's internal socketpair may need reviewed host execution;
retain the runner's network/database guards rather than disabling them.

The latest bounded Gemini smoke passed basil with egg, steak and Tom Yum, one request
each with the explicit free key, no retry/paid fallback. The actual basil output
included `set_aside` between egg frying and the next oil-heating cycle. This is
three-sample evidence, not a universal recipe-quality result. Local grammar/UI/HTTP
acceptance, actual doneness, full vessel/mixture/sub-batch state and grounded
nutrition were not established by that smoke. No additional live calls are needed
for Git publication; raw evidence stays in the local ignored `tmp`/`docs` directories.

## Publication verification (25 October 2026)

The isolated HEAD-plus-32-path candidate passes 1,100 backend tests
(1,098 passed, 2 skipped) in 185.910 seconds, with zero offline guard
violations and process exit 0. It excludes unrelated UI, seed tags and two
history timing-only fixture changes. Existing source/working changes remain
local; raw model responses and credentials are not part of this commit.

A redundant blank EOF line in one test was normalized after the full run; its
AST is identical and all six focused key-routing tests pass afterward (guards 0).
