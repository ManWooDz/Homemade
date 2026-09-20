import unittest

from finetune.exclusion import find_excluded_recipes
from finetune.recipe_source import Recipe


class FindExcludedRecipesTests(unittest.TestCase):
    def test_known_near_duplicate_is_excluded(self):
        recipes = [
            Recipe(dish_name="ส้มตำแตงร้าน", ingredient_lines=["แตงกวา 3 ผล"], instruction_text="ตำ"),
            Recipe(dish_name="แกงจืดต้นคะน้า", ingredient_lines=["คะน้า 1 กำ"], instruction_text="ต้ม"),
        ]
        fixtures = ["Som Tam", "Egg Fried Rice"]
        excluded = find_excluded_recipes(recipes, fixtures, keyword_pairs=[("ส้มตำ", "Som Tam")])
        self.assertEqual([r.dish_name for r in excluded], ["ส้มตำแตงร้าน"])

    def test_no_overlap_excludes_nothing(self):
        recipes = [Recipe(dish_name="แกงจืดต้นคะน้า", ingredient_lines=[], instruction_text="")]
        excluded = find_excluded_recipes(recipes, ["Egg Fried Rice"], keyword_pairs=[("ส้มตำ", "Som Tam")])
        self.assertEqual(excluded, [])

    def test_default_keyword_pairs_catch_both_known_near_duplicates(self):
        recipes = [
            Recipe(dish_name="ส้มตำแตงร้าน", ingredient_lines=[], instruction_text=""),
            Recipe(dish_name="ยำปลาหมึกสด", ingredient_lines=[], instruction_text=""),
            Recipe(dish_name="แกงจืดต้นคะน้า", ingredient_lines=[], instruction_text=""),
        ]
        fixtures = ["Som Tam", "Stir-Fried Squid", "Egg Fried Rice"]
        excluded = find_excluded_recipes(recipes, fixtures)  # default DISH_FAMILY_KEYWORD_PAIRS
        self.assertEqual(
            {r.dish_name for r in excluded}, {"ส้มตำแตงร้าน", "ยำปลาหมึกสด"}
        )


if __name__ == "__main__":
    unittest.main()
