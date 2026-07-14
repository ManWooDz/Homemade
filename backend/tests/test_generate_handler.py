import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from main import (
    GenerateRecipeTextRequest,
    call_agentic_llm,
    check_nutrition,
    generate_recipe_text,
    validate_recipe,
)


VALID_RECIPE = {
    "recipe_name": "Thai Basil Pork",
    "servings": 2,
    "adjusted_ingredients": [
        "หมูสับ 200 กรัม",
        "ใบกะเพรา 1 ถ้วย",
        "น้ำมัน 1 ช้อนโต๊ะ",
    ],
    "diet_tags": ["Thai"],
    "nutrition": {
        "basis": "per_serving",
        "calories": 420,
        "protein_g": 28,
        "carbs_g": 18,
        "fat_g": 24,
    },
    "instructions": [
        "1. ตั้งกระทะใส่น้ำมันแล้วผัดหมูให้สุก",
        "2. ใส่ใบกะเพรา",
    ],
    "safety_warning": "ระวังความร้อนขณะประกอบอาหาร",
}


class GenerateRecipeHandlerTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def make_request():
        return GenerateRecipeTextRequest(
            recipe={"name": "Custom Recipe from Fridge"},
            ingredients=[{"id": 1, "name": "minced pork"}],
            preferences={"allergy": "", "taste": "", "equipment": "", "extra": ""},
        )

    async def run_retry_case(self, invalid_recipe):
        responses = [invalid_recipe, deepcopy(VALID_RECIPE)]
        feedbacks = []

        def fake_llm(ingredients, user_prefs, base_recipe, feedback=None):
            feedbacks.append(feedback)
            return responses.pop(0)

        with patch("main.call_agentic_llm", side_effect=fake_llm) as mock_llm:
            response = await generate_recipe_text(self.make_request())

        return response, mock_llm, feedbacks

    async def test_handler_sends_presence_names_without_quantity(self):
        captured = {}

        def fake_llm(ingredients, user_prefs, base_recipe, feedback=None):
            captured["ingredients"] = ingredients
            return VALID_RECIPE

        request = GenerateRecipeTextRequest(
            recipe={"name": "Custom Recipe from Fridge"},
            ingredients=[
                {
                    "id": 1,
                    "name": "minced pork",
                    "quantity": "250 grams",
                    "image": "pork.png",
                }
            ],
            preferences={"allergy": "", "taste": "", "equipment": "", "extra": ""},
        )

        with patch("main.call_agentic_llm", side_effect=fake_llm) as mock_llm:
            response = await generate_recipe_text(request)

        self.assertEqual(response["status"], "success")
        self.assertEqual(captured["ingredients"], ["minced pork"])
        self.assertEqual(response["data"]["servings"], 2)
        self.assertEqual(response["data"]["nutrition"]["basis"], "per_serving")
        mock_llm.assert_called_once()

    async def test_handler_retries_none_or_non_dictionary_recipe(self):
        for malformed in (None, ["not", "a", "recipe"]):
            with self.subTest(malformed=malformed):
                response, mock_llm, feedbacks = await self.run_retry_case(malformed)

                self.assertEqual(response["status"], "success")
                self.assertEqual(mock_llm.call_count, 2)
                self.assertEqual(feedbacks, [None, "Invalid recipe"])

    async def test_handler_retries_missing_or_wrong_nutrient_value(self):
        invalid_recipes = []

        missing = deepcopy(VALID_RECIPE)
        missing["nutrition"].pop("protein_g")
        invalid_recipes.append((missing, "Invalid nutrition value: protein_g"))

        wrong_type = deepcopy(VALID_RECIPE)
        wrong_type["nutrition"]["fat_g"] = "24"
        invalid_recipes.append((wrong_type, "Invalid nutrition value: fat_g"))

        for invalid_recipe, expected_feedback in invalid_recipes:
            with self.subTest(expected_feedback=expected_feedback):
                response, mock_llm, feedbacks = await self.run_retry_case(
                    invalid_recipe
                )

                self.assertEqual(response["status"], "success")
                self.assertEqual(mock_llm.call_count, 2)
                self.assertEqual(feedbacks, [None, expected_feedback])

    async def test_handler_retries_invalid_diet_tags_or_safety_warning(self):
        invalid_recipes = []

        missing_tags = deepcopy(VALID_RECIPE)
        missing_tags.pop("diet_tags")
        invalid_recipes.append((missing_tags, "Invalid diet tags"))

        wrong_tags = deepcopy(VALID_RECIPE)
        wrong_tags["diet_tags"] = ["Thai", " "]
        invalid_recipes.append((wrong_tags, "Invalid diet tags"))

        missing_warning = deepcopy(VALID_RECIPE)
        missing_warning.pop("safety_warning")
        invalid_recipes.append((missing_warning, "Invalid safety warning"))

        wrong_warning = deepcopy(VALID_RECIPE)
        wrong_warning["safety_warning"] = []
        invalid_recipes.append((wrong_warning, "Invalid safety warning"))

        for invalid_recipe, expected_feedback in invalid_recipes:
            with self.subTest(expected_feedback=expected_feedback):
                response, mock_llm, feedbacks = await self.run_retry_case(
                    invalid_recipe
                )

                self.assertEqual(response["status"], "success")
                self.assertEqual(mock_llm.call_count, 2)
                self.assertEqual(feedbacks, [None, expected_feedback])

    async def test_handler_retries_prohibited_stock_conclusions(self):
        invalid_recipes = []

        instruction_claim = deepcopy(VALID_RECIPE)
        instruction_claim["instructions"][0] = "วัตถุดิบไม่พอ ต้องซื้อเพิ่ม"
        invalid_recipes.append(instruction_claim)

        warning_claim = deepcopy(VALID_RECIPE)
        warning_claim["safety_warning"] = "Not enough ingredients; must buy more."
        invalid_recipes.append(warning_claim)

        positive_instruction_claim = deepcopy(VALID_RECIPE)
        positive_instruction_claim["instructions"][0] = (
            "มีวัตถุดิบเพียงพอ เริ่มทำอาหารได้"
        )
        invalid_recipes.append(positive_instruction_claim)

        positive_warning_claim = deepcopy(VALID_RECIPE)
        positive_warning_claim["safety_warning"] = (
            "You have enough ingredients; ingredients are sufficient."
        )
        invalid_recipes.append(positive_warning_claim)

        for invalid_recipe in invalid_recipes:
            with self.subTest(invalid_recipe=invalid_recipe):
                response, mock_llm, feedbacks = await self.run_retry_case(
                    invalid_recipe
                )

                self.assertEqual(response["status"], "success")
                self.assertEqual(mock_llm.call_count, 2)
                self.assertEqual(feedbacks, [None, "Prohibited stock conclusion"])

    def test_validate_recipe_preflights_shape_before_six_stages(self):
        try:
            result = validate_recipe({}, ["minced pork"], {})
        except Exception as exc:
            self.fail(f"validation raised {type(exc).__name__}: {exc}")

        self.assertEqual(
            result, {"status": "fail", "reason": "Invalid recipe name"}
        )

    def test_check_nutrition_is_defensive_when_called_directly(self):
        for recipe in (None, {}, {"nutrition": None}):
            with self.subTest(recipe=recipe):
                try:
                    result = check_nutrition(recipe)
                except Exception as exc:
                    self.fail(f"nutrition check raised {type(exc).__name__}: {exc}")
                self.assertEqual(result[0], False)

    def test_prompt_defines_servings_recipe_totals_and_per_serving_nutrition(self):
        captured = {}

        def fake_generate_content(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text='{"recipe_name": "captured"}')

        fake_client = SimpleNamespace(
            models=SimpleNamespace(generate_content=fake_generate_content)
        )

        with patch("main.client", fake_client):
            call_agentic_llm(["minced pork"], {}, {"name": "test"})

        prompt = captured["contents"]
        self.assertIn("servings คือจำนวนที่เสิร์ฟของสูตรนี้", prompt)
        self.assertIn(
            "ปริมาณใน adjusted_ingredients ต้องเป็นปริมาณรวมสำหรับทั้งสูตร ซึ่งครอบคลุมจำนวนที่เสิร์ฟตาม servings",
            prompt,
        )
        self.assertIn(
            "ค่า calories, protein_g, carbs_g และ fat_g ใน nutrition ต้องเป็นค่าต่อ 1 ที่เสิร์ฟ",
            prompt,
        )
        self.assertIn(
            "หากประมาณค่าโภชนาการเป็นค่ารวมทั้งสูตร ต้องหารด้วย servings ก่อนตอบ",
            prompt,
        )


if __name__ == "__main__":
    unittest.main()
