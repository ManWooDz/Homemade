import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from main import (
    GenerateRecipeTextRequest,
    call_agentic_llm,
    check_nutrition,
    generate_recipe_text,
    save_generate_history,
    validate_recipe,
)
from nutrition.calculator import NutritionResult

_STUB_NUTRITION_RESULT = NutritionResult(
    nutrition={"basis": "per_serving", "calories": 1.0, "protein_g": 1.0, "carbs_g": 1.0, "fat_g": 1.0},
    partially_estimated=False,
    partially_estimated_reasons=[],
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

TEST_USER = SimpleNamespace(id=7)
TEST_DB = MagicMock()  # stands in for the request Session; handler calls db.close()


async def call_handler(request):
    return await generate_recipe_text(request, current_user=TEST_USER, db=TEST_DB)


class GenerateRecipeHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        personalization_patcher = patch(
            "main.get_personalization_for_request",
            new=AsyncMock(return_value=None),
        )
        self.mock_personalization = personalization_patcher.start()
        self.addCleanup(personalization_patcher.stop)

        patcher = patch("main.compute_recipe_nutrition", return_value=_STUB_NUTRITION_RESULT)
        self.mock_compute_nutrition = patcher.start()
        self.addCleanup(patcher.stop)

        history_patcher = patch("main.save_generate_history", return_value=101)
        self.mock_save_history = history_patcher.start()
        self.addCleanup(history_patcher.stop)

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
            response = await call_handler(self.make_request())

        return response, mock_llm, feedbacks

    async def test_request_session_is_closed_before_any_llm_call(self):
        # get_current_user's lookup opens a transaction on this Session; it must
        # be ended before the (slow) LLM calls so no connection sits idle in
        # transaction across them.
        events = []
        db = MagicMock()
        db.close.side_effect = lambda: events.append("close")

        def fake_llm(ingredients, user_prefs, base_recipe, feedback=None):
            events.append("llm")
            return deepcopy(VALID_RECIPE)

        with patch("main.call_agentic_llm", side_effect=fake_llm):
            response = await generate_recipe_text(self.make_request(), current_user=TEST_USER, db=db)

        self.assertEqual(response["status"], "success")
        self.assertEqual(events[0], "close")
        self.assertIn("llm", events)
        self.assertLess(events.index("close"), events.index("llm"))

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
            response = await call_handler(request)

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

    async def test_final_output_nutrition_is_replaced_by_computed_value(self):
        with patch("main.call_agentic_llm", side_effect=[deepcopy(VALID_RECIPE)]):
            response = await call_handler(self.make_request())

        self.assertEqual(response["data"]["nutrition"], _STUB_NUTRITION_RESULT.nutrition)
        self.assertEqual(response["data"]["llm_estimated_nutrition"], VALID_RECIPE["nutrition"])
        self.assertEqual(response["data"]["nutrition_partially_estimated"], False)
        self.assertEqual(response["data"]["computed_nutrition"], _STUB_NUTRITION_RESULT.nutrition)
        self.mock_compute_nutrition.assert_called_once()

    async def test_partially_estimated_result_keeps_llm_guess_and_exposes_computed_separately(self):
        partial = NutritionResult(
            nutrition={"basis": "per_serving", "calories": 2.0, "protein_g": 2.0, "carbs_g": 2.0, "fat_g": 2.0},
            partially_estimated=True,
            partially_estimated_reasons=["unparsed quantity: ใบกะเพรา 1 ถ้วย"],
        )
        self.mock_compute_nutrition.return_value = partial
        with patch("main.call_agentic_llm", side_effect=[deepcopy(VALID_RECIPE)]):
            response = await call_handler(self.make_request())

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["data"]["nutrition"], VALID_RECIPE["nutrition"])
        self.assertNotEqual(response["data"]["nutrition"], partial.nutrition)
        self.assertEqual(response["data"]["computed_nutrition"], partial.nutrition)
        self.assertEqual(response["data"]["llm_estimated_nutrition"], VALID_RECIPE["nutrition"])
        self.assertEqual(response["data"]["nutrition_partially_estimated"], True)

    async def test_sanity_bound_failure_on_clean_computed_result_flags_and_keeps_llm_guess(self):
        for bad_calories in (3500.0, -5.0):
            with self.subTest(calories=bad_calories):
                insane = NutritionResult(
                    nutrition={"basis": "per_serving", "calories": bad_calories, "protein_g": 1.0, "carbs_g": 1.0, "fat_g": 1.0},
                    partially_estimated=False,
                    partially_estimated_reasons=[],
                )
                self.mock_compute_nutrition.return_value = insane
                with patch("main.call_agentic_llm", side_effect=[deepcopy(VALID_RECIPE)]):
                    response = await call_handler(self.make_request())

                self.assertEqual(response["status"], "success")
                self.assertEqual(response["data"]["nutrition_partially_estimated"], True)
                self.assertEqual(response["data"]["nutrition"], VALID_RECIPE["nutrition"])
                self.assertEqual(response["data"]["computed_nutrition"], insane.nutrition)

    async def test_engine_failure_keeps_llm_guess_and_flags_instead_of_erroring(self):
        self.mock_compute_nutrition.side_effect = RuntimeError("db exploded")
        with patch("main.call_agentic_llm", side_effect=[deepcopy(VALID_RECIPE)]):
            response = await call_handler(self.make_request())

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["data"]["nutrition"], VALID_RECIPE["nutrition"])
        self.assertEqual(response["data"]["nutrition_partially_estimated"], True)
        self.assertNotIn("computed_nutrition", response["data"])

    async def test_shared_valid_recipe_fixture_is_not_mutated(self):
        # (rev 3) Regression test: test_handler_sends_presence_names_
        # without_quantity (elsewhere in this file) passes VALID_RECIPE
        # itself, not a copy, as call_agentic_llm's return value -- proves
        # main.py doesn't mutate it in place.
        original_nutrition = deepcopy(VALID_RECIPE["nutrition"])
        with patch("main.call_agentic_llm", side_effect=[VALID_RECIPE]):
            await call_handler(self.make_request())
        self.assertEqual(VALID_RECIPE["nutrition"], original_nutrition)

    async def test_history_writer_gets_approved_output_and_id_is_returned(self):
        request = self.make_request()
        with patch("main.call_agentic_llm", side_effect=[deepcopy(VALID_RECIPE)]):
            response = await generate_recipe_text(request, current_user=TEST_USER, db=TEST_DB)

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["data"]["history_id"], 101)
        self.mock_save_history.assert_called_once()
        db, user, passed_request, final_output = self.mock_save_history.call_args.args
        self.assertIs(db, TEST_DB)
        self.assertIs(user, TEST_USER)
        self.assertIs(passed_request, request)
        expected = dict(response["data"])
        expected.pop("history_id")
        personalization = expected.pop("personalization")
        self.assertEqual(final_output, expected)
        self.assertNotIn("history_id", final_output)
        self.assertNotIn("personalization", final_output)
        self.assertEqual(
            personalization,
            {"applied": False, "positives": 0, "negatives": 0},
        )

    async def test_history_write_failure_still_returns_recipe(self):
        self.mock_save_history.return_value = None
        with patch("main.call_agentic_llm", side_effect=[deepcopy(VALID_RECIPE)]):
            response = await call_handler(self.make_request())
        self.assertEqual(response["status"], "success")
        self.assertIsNone(response["data"]["history_id"])
        self.assertEqual(response["data"]["recipe_name"], VALID_RECIPE["recipe_name"])

    async def test_history_not_written_when_generation_fails(self):
        with patch("main.call_agentic_llm", return_value=None):
            response = await call_handler(self.make_request())
        self.assertEqual(response["status"], "error")
        self.mock_save_history.assert_not_called()


class SaveGenerateHistoryTests(unittest.TestCase):
    def test_swallows_db_errors_and_logs_safely(self):
        db = MagicMock()
        with patch("main.insert_generate_history", side_effect=RuntimeError("บันทึกไม่ได้ → 🌶️")), \
                patch("main._print_safe") as print_safe:
            # request must have .recipe, so the failure comes from the insert,
            # not from an AttributeError before it.
            result = save_generate_history(db, TEST_USER, SimpleNamespace(recipe={}), {"recipe_name": "X"})
        self.assertIsNone(result)
        db.rollback.assert_called_once()
        print_safe.assert_called_once()

    def test_returns_inserted_id(self):
        with patch("main.insert_generate_history", return_value=55) as insert:
            request = SimpleNamespace(recipe={"id": 5})
            result = save_generate_history(TEST_DB, TEST_USER, request, {"recipe_name": "X"})
        self.assertEqual(result, 55)
        insert.assert_called_once_with(
            TEST_DB, user_id=7, request_recipe={"id": 5}, final_output={"recipe_name": "X"}
        )


if __name__ == "__main__":
    unittest.main()
