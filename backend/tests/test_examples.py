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

    def test_masks_instructions_to_none_when_no_clause_boundary_can_avoid_leaking(self):
        """Regression test for a real bug found against the actual
        pythainlp/thai_food_v1.0 dataset (not hypothetical): most real
        instruction_text is punctuation-free running Thai prose with no
        sentence/clause boundary near the dropped ingredient's mention, so
        the whole instruction is one undifferentiated clause that still
        names the dropped ingredient. Full instruction supervision must be
        masked (None) rather than shipped leaking the dropped name --
        never fall back to unsplittable full text, and never shred the
        text into individual words/characters either."""
        recipe = Recipe(
            dish_name="ยำไข่ปลาดุก",
            ingredient_lines=["ไข่ปลาดุก 200 กรัม", "มะม่วงดิบ 1 ผล", "น้ำปลา 2 ช้อนโต๊ะ"],
            instruction_text=(
                "เอาไข่ปลาดุกที่นึ่งใส่จาน ปอกมะม่วงดิบและผ่าบาง ๆ หั่นเป็นฝอย "
                "ซอยหัวหอม ใส่รวมกับไข่ปลาดุก เมื่อจะรับประทานใส่น้ำปลาตามต้องการ "
                "คลุกหั่นพริกขี้หนูโรยหน้า"
            ),
        )
        examples = build_tier_a_examples(recipe)
        self.assertGreater(len(examples), 0)
        first = examples[0]
        self.assertEqual(first["tier"], "A")
        # the ingredient target must still be correct even though
        # instructions get masked
        self.assertNotIn("น้ำปลา 2 ช้อนโต๊ะ", first["target_adjusted_ingredients"])
        # instructions must be masked, not a leaking full-text fallback
        self.assertIsNone(first["target_instructions"])

    def test_numbered_step_instructions_split_without_orphan_number_fragments(self):
        """Regression test for a real (non-leak) bug found against the
        actual dataset's small numbered-step minority: splitting must not
        produce a standalone clause that is just a step number ("1.",
        "2.") with no real content, and must not leak the dropped
        ingredient's name into any kept clause."""
        recipe = Recipe(
            dish_name="น้ำพริกกะปิ",
            ingredient_lines=["กุ้งแห้ง 50 กรัม", "กระเทียม 5 กลีบ", "น้ำตาลปี๊บ 1 ช้อนโต๊ะ"],
            instruction_text=(
                "1. โขลกกระเทียมและพริกให้ละเอียด ใส่กุ้งแห้งโขลกต่อจนเข้ากัน\n\n"
                "2. ปรุงรสด้วยน้ำตาลปี๊บและน้ำปลาตามชอบ\n\n"
                "3. ชิมรสให้กลมกล่อมแล้วตักใส่ถ้วย"
            ),
        )
        examples = build_tier_a_examples(recipe)
        self.assertGreater(len(examples), 0)
        first = examples[0]
        self.assertEqual(first["tier"], "A")
        self.assertNotIn("น้ำตาลปี๊บ 1 ช้อนโต๊ะ", first["target_adjusted_ingredients"])
        self.assertIsNotNone(first["target_instructions"])
        for clause in first["target_instructions"]:
            self.assertFalse(
                clause.strip().rstrip(".").isdigit(),
                f"orphan step-number fragment leaked into target_instructions: {clause!r}",
            )
        joined = " ".join(first["target_instructions"])
        self.assertNotIn("น้ำตาลปี๊บ", joined)


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
