import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from generators.prompts import build_recipe_prompt  # noqa: E402

from .recipe_source import Recipe
from .thai_text import extract_ingredient_name

# Verified against the real dataset 2026-09-21 (design spec §4.1): these
# keywords account for 341 matches across 159 recipes, mean relative
# position 0.711, 82.4% in the back half of the ingredient list.
SEASONING_KEYWORDS = [
    "น้ำปลา", "น้ำตาล", "เกลือ", "พริกไทย", "ซีอิ๊ว", "น้ำมัน",
    "ผงชูรส", "มะนาว", "น้ำส้มสายชู", "กะปิ",
]

_STAPLES = ["เกลือ", "พริกไทย", "น้ำมัน", "น้ำปลา", "ซีอิ๊ว", "น้ำตาล", "น้ำเปล่า"]


def is_non_essential(ingredient_line: str, position: int, total: int) -> bool:
    """Design spec §4.1's dual rule: a seasoning-keyword match AND back-half
    list position, both required. total<=1 never flags (nothing to gate
    against)."""
    if total <= 1:
        return False
    relative_position = position / (total - 1)
    is_seasoning = any(kw in ingredient_line for kw in SEASONING_KEYWORDS)
    return is_seasoning and relative_position >= 0.5


# Clause-boundary points for `_drop_instruction_clauses_mentioning`. The
# draft's original pattern -- (?<=[.!?])\s+|(?<=กัน)\s+|(?<=สุก)\s+ -- was
# verified empirically against real recipes from the actual
# pythainlp/thai_food_v1.0 dataset (not just the brief's single synthetic
# test string) and found unsafe: of an 8-recipe sample that had a
# non-essential ingredient to drop, only 3 had >=2 boundary matches;
# the other 5 fell through to the draft's `instruction_text.split(" ")`
# fallback, which shreds real instruction text into individual words,
# bare digits ("6", "3", "10") and stray punctuation-only tokens ("ๆ")
# as standalone "clauses" -- e.g. dish "ข้าวเม่าทอด" -> 21 fragments
# including "โขลก", "ด้วยครกให้", "ๆ". That fallback is a real data
# corruption bug that this project's own MEMORY.md's lesson about
# exact-substring/heuristic checks applies to directly: passing the
# brief's one test case was not evidence the heuristic was safe.
#
# Root cause: the source dataset's instruction_text is mostly
# punctuation-free running Thai prose (only 10/146 real recipes contain
# any '.', and only 3/146 use numbered steps -- confirmed by loading the
# real dataset xlsx, not assumed), so period/exclaim/question-mark
# boundaries rarely fire, and "กัน"/"สุก" alone are too sparse. Fix:
# broaden the connector-word boundary set to a handful of common Thai
# clause-sequencing words this dataset's prose actually uses to chain
# cooking actions ("แล้ว" = "then/having done X", "จากนั้น" = "after
# that", "จึง" = "so/then") -- and, critically, remove the word-level
# split fallback entirely. If no connector boundary is found at all, the
# whole instruction_text is treated as one clause and either kept or
# dropped in full -- coarser than ideal, but it never breaks Thai words
# apart, which is the one thing a training target absolutely cannot do.
_CLAUSE_SPLIT_PATTERN = re.compile(
    r"(?<=[.!?])\s+|(?<=กัน)\s+|(?<=สุก)\s+|(?<=แล้ว)\s+|(?<=จากนั้น)\s+|(?<=จึง)\s+"
)

# A small minority of real recipes (3/146 in the dataset) use an explicit
# "1. ... 2. ... 3. ..." numbered-step convention (the brief itself
# anticipated this as worth special-casing "where present"). Without
# special-casing, _CLAUSE_SPLIT_PATTERN's generic (?<=[.!?])\s+ boundary
# also fires on the step markers themselves (since the marker's period IS
# a "." followed by whitespace), producing a useless orphan "1." fragment
# as its own standalone clause and leaving "2."/"3." glued onto the tail
# of the preceding step's text instead of starting the next one --
# confirmed against the real numbered-step recipes in the dataset. Not a
# leak/safety issue (no ingredient names in a bare step-number token) but
# real to fix: numbered steps are already natural clause units, so this
# splits on them first and strips the marker before applying the generic
# connector pattern within each step.
_NUMBERED_STEP_SPLIT = re.compile(r"(?=\d+\.\s)")
_LEADING_STEP_NUMBER = re.compile(r"^\d+\.\s*")


def _split_into_clauses(instruction_text: str) -> list[str]:
    """Splits instruction_text into clause units, numbered-step-aware (see
    comment above _NUMBERED_STEP_SPLIT)."""
    steps = [s.strip() for s in _NUMBERED_STEP_SPLIT.split(instruction_text) if s.strip()]
    if len(steps) < 2:
        return [s.strip() for s in _CLAUSE_SPLIT_PATTERN.split(instruction_text) if s.strip()]
    parts = []
    for step in steps:
        step = _LEADING_STEP_NUMBER.sub("", step).strip()
        if step:
            parts.extend(p.strip() for p in _CLAUSE_SPLIT_PATTERN.split(step) if p.strip())
    return parts


def _drop_instruction_clauses_mentioning(instruction_text: str, dropped_names: list[str]) -> list[str] | None:
    """Splits instructions into clauses on Thai/ASCII clause-ish boundaries
    (see `_CLAUSE_SPLIT_PATTERN` above for why this set was chosen) and
    drops any clause that names a dropped ingredient -- deterministic
    string match, same technique check_ingredient_hallucination uses
    (design spec §4.2), never an LLM rewrite.

    Returns None (caller then masks target_instructions from the loss,
    same as Tier B) when clause-splitting genuinely cannot avoid leaking a
    dropped ingredient's name -- verified against the real
    pythainlp/thai_food_v1.0 dataset (146 recipes, 217 would-be Tier A
    examples) that this is not a rare edge case: many real instruction
    texts never hit any connector boundary at all (74/217 cases -- the
    whole instruction is one undifferentiated clause), and about half of
    those (46/217, ~21% of all Tier A examples) genuinely name the dropped
    ingredient somewhere in that one clause. Silently keeping the whole
    unsplit clause (the earlier `kept if kept else [instruction_text]`
    behavior) would have shipped training data that tells the model
    "don't include ingredient X" right next to instructions that mention
    X -- worse than no instruction supervision for that example. Full
    supervision is only returned when it's actually leak-free; a coarse
    but valid ingredients-only Tier A example (mirroring Tier B's
    None-instructions contract) is preferred over a leaking one."""
    parts = _split_into_clauses(instruction_text)
    kept = [s for s in parts if not any(name in s for name in dropped_names)]
    if not kept:
        return None
    joined = " ".join(kept)
    if any(name in joined for name in dropped_names):
        return None
    return kept


def build_tier_a_examples(recipe: Recipe) -> list[dict]:
    """Near-complete-subset, full supervision (design spec §4.2). Drops
    1-2 non-essential ingredients per generated example; staples only
    appear in the target if the source recipe itself listed them (never
    invented, per spec §4.3's rule applied to both tiers)."""
    total = len(recipe.ingredient_lines)
    non_essential_indices = [
        i for i, line in enumerate(recipe.ingredient_lines) if is_non_essential(line, i, total)
    ]
    if not non_essential_indices:
        return []

    examples = []
    for drop_count in (1, 2):
        if drop_count > len(non_essential_indices):
            break
        dropped_indices = set(non_essential_indices[:drop_count])
        remaining = [line for i, line in enumerate(recipe.ingredient_lines) if i not in dropped_indices]
        dropped_names = [extract_ingredient_name(recipe.ingredient_lines[i]) for i in dropped_indices]
        given_names = [extract_ingredient_name(line) for line in remaining]

        prompt = build_recipe_prompt(
            ingredients=given_names,
            user_prefs={"allergy": "", "taste": "", "equipment": "", "extra": ""},
            base_recipe={"name": recipe.dish_name, "servings": 2},
            feedback=None,
            include_example=True,
        )
        target_instructions = _drop_instruction_clauses_mentioning(recipe.instruction_text, dropped_names)
        examples.append(
            {
                "prompt": prompt,
                "target_adjusted_ingredients": remaining,
                "target_instructions": target_instructions,
                "tier": "A",
            }
        )
    return examples


def build_tier_b_examples(recipe: Recipe) -> list[dict]:
    """Sparse-subset, ingredients-only supervision (design spec §4.3) --
    the input shape where hallucination pressure is highest. instructions
    are masked (None), never generated or invented."""
    non_seasoning = [
        line for line in recipe.ingredient_lines
        if not any(kw in line for kw in SEASONING_KEYWORDS)
    ]
    if not non_seasoning:
        return []

    examples = []
    for given_count in (1, 2):
        if given_count > len(non_seasoning):
            break
        given_lines = non_seasoning[:given_count]
        given_names = [extract_ingredient_name(line) for line in given_lines]
        # Staples only if the source recipe actually used them (spec §4.3),
        # capped to at most one bonus staple beyond what's given. Tier B's
        # whole point is teaching tight adherence to a *sparse* given-set
        # (design spec §4.3) -- appending every staple the source recipe
        # happens to use (real recipes often use 2-4) would make the target
        # look like Tier A's near-complete-subset in miniature, diluting the
        # sparse-supervision signal this tier is for. One representative
        # staple keeps the example genuinely sparse while still teaching
        # "you may add a basic staple" rather than "add zero, ever."
        target_staples = [
            line for line in recipe.ingredient_lines
            if any(extract_ingredient_name(line) == s for s in _STAPLES)
            and line not in given_lines
        ]
        target = given_lines + target_staples[:1]

        prompt = build_recipe_prompt(
            ingredients=given_names,
            user_prefs={"allergy": "", "taste": "", "equipment": "", "extra": ""},
            base_recipe={"name": recipe.dish_name, "servings": 2},
            feedback=None,
            include_example=True,
        )
        examples.append(
            {
                "prompt": prompt,
                "target_adjusted_ingredients": target,
                "target_instructions": None,
                "tier": "B",
            }
        )
    return examples
