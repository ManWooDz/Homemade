from .recipe_source import Recipe
from .thai_text import dish_families_overlap

# Dish families present in the 15-case eval fixture set
# (backend/eval/fixtures/generator_eval_cases.json) as of 2026-09-20 --
# design spec §3.1. Each pair is (Thai form found in the source dataset's
# DishName, the transliterated/English form found in that fixture's
# actual base_recipe.name) -- anchored on the real fixture names, not
# generic category words, to avoid over-excluding unrelated recipes.
# Update this list if the fixture set's base_recipe names change; re-run
# find_excluded_recipes before rebuilding the training set whenever it does.
DISH_FAMILY_KEYWORD_PAIRS = [
    ("กะปิ", "Kapi"),              # Nam Prik Kapi
    ("ลาบ", "Larb"),               # Larb Moo
    ("แกงเขียวหวาน", "Kiew Wan"),   # Gaeng Kiew Wan Gai
    ("ข้าวผัด", "Fried Rice"),      # Egg Fried Rice, Khao Pad
    ("ผัดซีอิ๊ว", "Si Ew"),         # Moo Pad Si Ew
    ("สะเต๊ะ", "Satay"),           # Moo Satay
    ("เต้าหู้", "Tofu"),           # Tofu Soup
    ("ปลาหมึก", "Squid"),          # Stir-Fried Squid
    ("แกงจืด", "Jued"),            # Kaeng Jued Mara
    ("มะระ", "Mara"),              # Kaeng Jued Mara
    ("วุ้นเส้น", "Woon Sen"),      # Yum Woon Sen
    ("มัสมั่น", "Massaman"),       # Gaeng Massaman
    ("ต้มยำ", "Tom Yum"),          # Tom Yum Goong
    ("ส้มตำ", "Som Tam"),          # Som Tam
]


def find_excluded_recipes(
    recipes: list[Recipe],
    fixture_base_recipe_names: list[str],
    keyword_pairs: list[tuple[str, str]] | None = None,
) -> list[Recipe]:
    """Returns the subset of `recipes` whose dish_name shares a dish-family
    with any eval fixture's base_recipe name -- these must be dropped
    from the training pool before Task 6 samples from it, per design spec
    §3.1 (verified near-duplicates: ส้มตำแตงร้าน / Som Tam, ยำปลาหมึกสด /
    Stir-Fried Squid)."""
    pairs = keyword_pairs if keyword_pairs is not None else DISH_FAMILY_KEYWORD_PAIRS
    excluded = []
    for recipe in recipes:
        for fixture_name in fixture_base_recipe_names:
            if dish_families_overlap(recipe.dish_name, fixture_name, pairs):
                excluded.append(recipe)
                break
    return excluded
