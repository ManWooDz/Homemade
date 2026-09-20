import unittest

from finetune.examples import build_tier_a_examples, build_tier_b_examples, is_non_essential
from finetune.recipe_source import Recipe


class IsNonEssentialTests(unittest.TestCase):
    def test_seasoning_in_back_half_is_non_essential(self):
        # position 4 of 5 (0-indexed), i.e. back half
        self.assertTrue(is_non_essential("น้ำปลา 2 ช้อนโต๊ะ", position=4, total=5))

    def test_seasoning_in_front_half_is_not_flagged(self):
        # a seasoning word appearing first is unusual and NOT auto-dropped --
        # position gate exists precisely to avoid over-flagging (design spec §4.1)
        self.assertFalse(is_non_essential("น้ำปลา 2 ช้อนโต๊ะ", position=0, total=5))

    def test_non_seasoning_in_back_half_is_not_flagged(self):
        self.assertFalse(is_non_essential("หมูสับ 300 กรัม", position=4, total=5))


class BuildTierAExamplesTests(unittest.TestCase):
    def test_drops_one_non_essential_ingredient_and_matching_instruction_clause(self):
        recipe = Recipe(
            dish_name="ผัดกะเพราหมู",
            ingredient_lines=["หมูสับ 300 กรัม", "ใบกะเพรา 1 ถ้วย", "น้ำปลา 1 ช้อนโต๊ะ"],
            instruction_text="ผัดหมูสับกับน้ำมันจนสุก ปรุงรสด้วยน้ำปลา ใส่ใบกะเพราผัดให้เข้ากัน",
        )
        examples = build_tier_a_examples(recipe)
        self.assertGreater(len(examples), 0)
        first = examples[0]
        self.assertEqual(first["tier"], "A")
        self.assertNotIn("น้ำปลา 1 ช้อนโต๊ะ", first["target_adjusted_ingredients"])
        self.assertIsNotNone(first["target_instructions"])
        joined = " ".join(first["target_instructions"])
        self.assertNotIn("น้ำปลา", joined)


class BuildTierBExamplesTests(unittest.TestCase):
    def test_sparse_subset_masks_instructions(self):
        recipe = Recipe(
            dish_name="ผัดกะเพราหมู",
            ingredient_lines=["หมูสับ 300 กรัม", "ใบกะเพรา 1 ถ้วย", "น้ำปลา 1 ช้อนโต๊ะ", "น้ำมัน 1 ช้อนโต๊ะ"],
            instruction_text="ผัดหมูสับกับน้ำมันจนสุก ปรุงรสด้วยน้ำปลา ใส่ใบกะเพราผัดให้เข้ากัน",
        )
        examples = build_tier_b_examples(recipe)
        self.assertGreater(len(examples), 0)
        first = examples[0]
        self.assertEqual(first["tier"], "B")
        self.assertIsNone(first["target_instructions"])
        self.assertLessEqual(len(first["target_adjusted_ingredients"]), 2)


if __name__ == "__main__":
    unittest.main()
