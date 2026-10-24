# backend/tests/test_generators_prompts.py
import unittest

from generators.prompts import build_recipe_prompt


class BuildRecipePromptTests(unittest.TestCase):
    def test_current_prompt_estimates_final_elapsed_time_without_changing_legacy_training(self):
        for include_example in (False, True):
            prompt = build_recipe_prompt(["egg"], {}, {}, include_example=include_example)
            for text in ('"estimated_total_time"', '"min_minutes"', '"max_minutes"',
                         "รวมเวลาเตรียม ปรุง และรอ", "วัตถุดิบสำเร็จรูปที่ระบุถือว่าเตรียมแล้ว",
                         "ถ้าประเมินไม่ได้ให้ส่ง null", "ห้ามคัดลอกเวลาสูตรตั้งต้น"):
                self.assertIn(text, prompt)
        legacy = build_recipe_prompt(["egg"], {}, {}, include_example=True, structured_instructions=False)
        self.assertNotIn("estimated_total_time", legacy)

    def test_prompt_declares_all_used_ingredients_and_bounded_flavor_methods(self):
        for include_example in (False, True):
            prompt = build_recipe_prompt(["minced pork", "chives"], {}, {}, include_example=include_example)
            for text in ("ทุกวัตถุดิบที่ใช้ในขั้นตอน", "กุยช่าย", "หมูสับ", "เฉพาะผัดไทย/ผัดกะเพรา", "วิธีที่ไม่ใช้น้ำมันต้องระบุให้ชัด" if include_example else "ถ้าใช้วิธีไร้น้ำมันให้ระบุวิธีให้ชัด"):
                self.assertIn(text, prompt)

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

        prompt = build_recipe_prompt(["egg"], {}, {"name": "test"}, include_example=True)
        self.assertIn("ตัวอย่างที่ถูกต้อง", prompt)
        example = {"instructions": [{"action": "cut", "ingredients": ["i1"], "targets": [], "excluded": []}]}
        self.assertIn(json.dumps(example, ensure_ascii=False, indent=2), prompt)
        self.assertIn("i1=egg", prompt)
        self.assertNotIn("อกไก่ 300 กรัม", prompt)

    def test_legacy_training_prompt_keeps_prose_targets_compatible(self):
        prompt = build_recipe_prompt(["egg"], {}, {}, include_example=True, structured_instructions=False)
        self.assertIn('"instructions": ["1. ขั้นตอนแรก', prompt)
        self.assertIn("อกไก่ 300 กรัม", prompt)
        self.assertNotIn("รหัสวัตถุดิบที่ backend กำหนด", prompt)
        self.assertNotIn('"action":', prompt)


if __name__ == "__main__":
    unittest.main()
