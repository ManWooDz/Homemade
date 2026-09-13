# backend/tests/test_generators_prompts.py
import unittest

from generators.prompts import build_recipe_prompt


class BuildRecipePromptTests(unittest.TestCase):
    def test_prompt_includes_servings_and_per_serving_nutrition_rules(self):
        prompt = build_recipe_prompt(["minced pork"], {}, {"name": "test"})
        self.assertIn("servings คือจำนวนที่เสิร์ฟของสูตรนี้", prompt)
        self.assertIn(
            "ปริมาณใน adjusted_ingredients ต้องเป็นปริมาณรวมสำหรับทั้งสูตร ซึ่งครอบคลุมจำนวนที่เสิร์ฟตาม servings",
            prompt,
        )
        self.assertIn(
            "ค่า calories, protein_g, carbs_g และ fat_g ใน nutrition ต้องเป็นค่าต่อ 1 ที่เสิร์ฟ",
            prompt,
        )

    def test_prompt_has_no_feedback_section_when_feedback_is_none(self):
        prompt = build_recipe_prompt(["egg"], {}, {"name": "test"}, feedback=None)
        self.assertNotIn("ผลตรวจสอบจากรอบก่อนหน้า", prompt)

    def test_prompt_embeds_feedback_when_provided(self):
        prompt = build_recipe_prompt(["egg"], {}, {"name": "test"}, feedback="Invalid nutrition value: protein_g")
        self.assertIn("ผลตรวจสอบจากรอบก่อนหน้า", prompt)
        self.assertIn("Invalid nutrition value: protein_g", prompt)

    def test_prompt_forbids_ingredient_hallucination(self):
        prompt = build_recipe_prompt(["egg"], {}, {"name": "test"})
        self.assertIn("ห้ามมโนวัตถุดิบ", prompt)

    def test_prompt_requires_json_only_response(self):
        prompt = build_recipe_prompt(["egg"], {}, {"name": "test"})
        self.assertIn("ตอบกลับมาเป็นรูปแบบ JSON เท่านั้น", prompt)

    def test_include_example_false_by_default_matches_production_prompt(self):
        prompt = build_recipe_prompt(["egg"], {}, {"name": "test"})
        self.assertNotIn("ตัวอย่างที่ถูกต้อง", prompt)

    def test_include_example_true_appends_a_worked_example(self):
        import json

        from generators.prompts import FEW_SHOT_EXAMPLE_RECIPE

        prompt = build_recipe_prompt(["egg"], {}, {"name": "test"}, include_example=True)
        self.assertIn("ตัวอย่างที่ถูกต้อง", prompt)
        # the exact example dict must appear as valid, embedded JSON
        self.assertIn(json.dumps(FEW_SHOT_EXAMPLE_RECIPE, ensure_ascii=False, indent=2), prompt)


if __name__ == "__main__":
    unittest.main()
