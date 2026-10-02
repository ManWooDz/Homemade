import hashlib
import io
import json
import os
import unittest
from copy import deepcopy
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from google.genai.errors import ClientError

import main
from embeddings import EmbeddingError
from main import GenerateRecipeTextRequest
from nutrition.calculator import NutritionResult
from personalization.context import PersonalizationContext


PERSONALIZATION_KEY = "__personalization_context"
PROMPT_BLOCK = """<<<PERSONALIZATION_REFERENCE_DATA>>>
ข้อมูลอ้างอิงทดสอบ
<<<END_PERSONALIZATION_REFERENCE_DATA>>>"""

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

STUB_NUTRITION = NutritionResult(
    nutrition={"basis": "per_serving", "calories": 1.0, "protein_g": 1.0, "carbs_g": 1.0, "fat_g": 1.0},
    partially_estimated=False,
    partially_estimated_reasons=[],
)


def request(*, recipe_name="Custom Recipe from Fridge", taste="เผ็ด"):
    return GenerateRecipeTextRequest(
        recipe={"id": 12, "name": recipe_name, "servings": 2},
        ingredients=[
            {"id": 1, "name": "minced pork", "quantity": 1},
            {"id": 2, "name": "holy basil", "quantity": 1},
        ],
        preferences={
            "allergies": "",
            "taste": taste,
            "equipment": "กระทะ",
            "extra": "",
        },
    )


class TrackingSession:
    def __init__(self):
        self.events = []

    def close(self):
        self.events.append("close")

    def rollback(self):
        self.events.append("rollback")


class CloseFailSession(TrackingSession):
    def close(self):
        self.events.append("close")
        raise RuntimeError("close failed")


class PersonalizationGenerationPromptTests(unittest.TestCase):
    def test_provider_error_logs_omit_personalized_request_contents(self):
        private_feedback = "PRIVATE-RATING-FEEDBACK"
        private_message = "PRIVATE-PROVIDER-MESSAGE"
        context = PROMPT_BLOCK.replace("ข้อมูลอ้างอิงทดสอบ", private_feedback)

        def generate_content(**kwargs):
            raise ClientError(400, {
                "error": {
                    "code": 400,
                    "status": "INVALID_ARGUMENT",
                    "message": private_message,
                },
                "request": {"contents": kwargs["contents"]},
            })

        fake_client = SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        )
        output = io.StringIO()
        with patch("main.client", fake_client), redirect_stdout(output):
            response = main.call_agentic_llm(
                ["minced pork"],
                {"taste": "spicy", PERSONALIZATION_KEY: context},
                {"name": "test"},
                feedback="PRIVATE-CRITIC-FEEDBACK",
            )

        self.assertEqual(response["error"], "ไม่สามารถสร้างสูตรอาหารได้ในขณะนี้")
        logs = output.getvalue()
        self.assertIn("Gemini", logs)
        for private_text in (
            private_feedback,
            private_message,
            "PRIVATE-CRITIC-FEEDBACK",
            "<<<PERSONALIZATION_REFERENCE_DATA>>>",
            "<<<END_PERSONALIZATION_REFERENCE_DATA>>>",
        ):
            with self.subTest(private_text=private_text):
                self.assertNotIn(private_text, logs)
        self.assertIn("ClientError", logs)

    def _capture(self, prefs, feedback=None):
        captured = {}

        def generate_content(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text="{}")

        fake_client = SimpleNamespace(
            models=SimpleNamespace(generate_content=generate_content)
        )
        with patch("main.client", fake_client):
            main.call_agentic_llm(
                ["minced pork"], prefs, {"name": "test"}, feedback=feedback
            )
        return captured["contents"]

    def test_prompt_is_byte_identical_when_internal_key_is_absent(self):
        prompt = self._capture({"taste": "spicy"})
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        self.assertEqual(
            digest,
            "ad5b47aec8643b164e224738bf6be644c499f5722bb88d56461e1d8a645960c3",
        )

    def test_context_is_before_feedback_and_hard_rules_and_not_normal_preferences(self):
        prefs = {
            "taste": "spicy",
            main._LLM_FORBIDDEN_KEY: "กุ้ง" + main._LLM_FORBIDDEN_SUFFIX,
            PERSONALIZATION_KEY: PROMPT_BLOCK,
        }
        prompt = self._capture(prefs, feedback="fix salt")
        visible_prefs = {
            "taste": "spicy",
            main._LLM_FORBIDDEN_KEY: "กุ้ง" + main._LLM_FORBIDDEN_SUFFIX,
        }

        self.assertEqual(prompt.count(PROMPT_BLOCK), 1)
        self.assertLess(prompt.index(PROMPT_BLOCK), prompt.index("ผลตรวจสอบจากรอบก่อนหน้า"))
        self.assertLess(prompt.index(PROMPT_BLOCK), prompt.index("กฎเหล็กด้านความปลอดภัย"))
        self.assertEqual(prompt.count(str(visible_prefs)), 2)
        self.assertNotIn(PERSONALIZATION_KEY, prompt)
        self.assertIn(main._LLM_FORBIDDEN_KEY, prompt)

    def test_context_block_is_identical_on_every_retry(self):
        prefs = {"taste": "spicy", PERSONALIZATION_KEY: PROMPT_BLOCK}
        first = self._capture(prefs)
        retry = self._capture(prefs, feedback="Invalid ingredient found")
        for prompt in (first, retry):
            start = prompt.index("<<<PERSONALIZATION_REFERENCE_DATA>>>")
            end = prompt.index("<<<END_PERSONALIZATION_REFERENCE_DATA>>>")
            rendered = prompt[start:end + len("<<<END_PERSONALIZATION_REFERENCE_DATA>>>")]
            self.assertEqual(rendered, PROMPT_BLOCK)


class PersonalizationGenerationOrchestrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_switch_skips_database_and_embedding(self):
        db = MagicMock()
        with patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "0"}), \
                patch("main.count_embedded_signals", side_effect=AssertionError("counted")), \
                patch("main.embed_request_queries", side_effect=AssertionError("embedded")):
            result = await main.get_personalization_for_request(
                db,
                7,
                recipe_name="Custom Recipe from Fridge",
                ingredient_names=["minced pork"],
                taste="spicy",
                user_prefs={"allergies": ""},
                resolved_blocks={},
            )
        self.assertIsNone(result)
        db.close.assert_not_called()

    async def test_cold_start_closes_count_transaction_and_never_embeds(self):
        db = TrackingSession()
        with patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "1"}), \
                patch("main.count_embedded_signals", return_value=2), \
                patch("main.embed_request_queries", side_effect=AssertionError("embedded")):
            result = await main.get_personalization_for_request(
                db,
                7,
                recipe_name="Pad Kra Pao",
                ingredient_names=["minced pork"],
                taste="spicy",
                user_prefs={"allergies": ""},
                resolved_blocks={},
            )
        self.assertIsNone(result)
        self.assertEqual(db.events, ["close"])

    async def test_count_close_failures_fail_open_before_embedding(self):
        for signal_count in (2, 3):
            with self.subTest(signal_count=signal_count):
                db = CloseFailSession()
                threadpool = AsyncMock(side_effect=AssertionError("embedded"))
                with patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "1"}), \
                        patch("main.count_embedded_signals", return_value=signal_count), \
                        patch("main.run_in_threadpool", new=threadpool):
                    result = await main.get_personalization_for_request(
                        db,
                        7,
                        recipe_name="Pad Kra Pao",
                        ingredient_names=["minced pork"],
                        taste="spicy",
                        user_prefs={"allergies": ""},
                        resolved_blocks={},
                    )
                self.assertIsNone(result)
                self.assertEqual(db.events, ["close", "rollback"])
                threadpool.assert_not_awaited()

    async def test_count_is_closed_before_threadpool_embedding_and_query_is_production_shaped(self):
        db = TrackingSession()
        calls = []

        async def fake_threadpool(function, texts):
            calls.append((function, texts, list(db.events)))
            return [[1.0] + [0.0] * 767]

        expected = PersonalizationContext(PROMPT_BLOCK, 2, 1)
        with patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "1"}), \
                patch("main.count_embedded_signals", return_value=3), \
                patch("main.run_in_threadpool", side_effect=fake_threadpool), \
                patch("main.build_personalization_context", return_value=expected) as build:
            result = await main.get_personalization_for_request(
                db,
                7,
                recipe_name="Pad Kra Pao",
                ingredient_names=["minced pork", "holy basil"],
                taste="spicy",
                user_prefs={"allergies": ""},
                resolved_blocks={},
            )

        self.assertIs(result, expected)
        self.assertEqual(calls[0][0], main.embed_request_queries)
        self.assertEqual(
            calls[0][1],
            ["Pad Kra Pao | วัตถุดิบ: minced pork, holy basil | taste: spicy"],
        )
        self.assertEqual(calls[0][2], ["close"])
        self.assertEqual(db.events, ["close", "close"])
        self.assertEqual(build.call_args.kwargs["query_embedding"], [1.0] + [0.0] * 767)

    async def test_custom_frontend_label_is_omitted_from_query(self):
        db = TrackingSession()
        seen = []

        async def fake_threadpool(_function, texts):
            seen.extend(texts)
            return [[1.0] + [0.0] * 767]

        with patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "1"}), \
                patch("main.count_embedded_signals", return_value=3), \
                patch("main.run_in_threadpool", side_effect=fake_threadpool), \
                patch("main.build_personalization_context", return_value=None):
            await main.get_personalization_for_request(
                db,
                7,
                recipe_name="Custom Recipe from Fridge",
                ingredient_names=["minced pork"],
                taste="ไม่ระบุ",
                user_prefs={"allergies": ""},
                resolved_blocks={},
            )
        self.assertEqual(seen, ["วัตถุดิบ: minced pork"])

    async def test_embedding_failures_fail_open_and_close_session(self):
        failures = (
            EmbeddingError("GEMINI_API_KEY is required"),
            TimeoutError("timeout"),
            RuntimeError("429"),
            EmbeddingError("invalid response"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__, message=str(failure)):
                db = TrackingSession()
                with patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "1"}), \
                        patch("main.count_embedded_signals", return_value=3), \
                        patch("main.run_in_threadpool", side_effect=failure):
                    result = await main.get_personalization_for_request(
                        db,
                        7,
                        recipe_name="Pad Kra Pao",
                        ingredient_names=["minced pork"],
                        taste="spicy",
                        user_prefs={"allergies": ""},
                        resolved_blocks={},
                    )
                self.assertIsNone(result)
                self.assertEqual(db.events[-1], "close")

    async def test_database_and_builder_failures_rollback_close_and_fail_open(self):
        for stage in ("count", "builder"):
            with self.subTest(stage=stage):
                db = TrackingSession()
                count = RuntimeError("db") if stage == "count" else 3
                builder = RuntimeError("allergy or builder") if stage == "builder" else None
                with patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "1"}), \
                        patch("main.count_embedded_signals", side_effect=count if isinstance(count, Exception) else None,
                              return_value=count if isinstance(count, int) else None), \
                        patch("main.run_in_threadpool", new=AsyncMock(return_value=[[1.0] + [0.0] * 767])), \
                        patch("main.build_personalization_context", side_effect=builder):
                    result = await main.get_personalization_for_request(
                        db,
                        7,
                        recipe_name="Pad Kra Pao",
                        ingredient_names=["minced pork"],
                        taste="spicy",
                        user_prefs={"allergies": ""},
                        resolved_blocks={},
                    )
                self.assertIsNone(result)
                self.assertIn("rollback", db.events)
                self.assertEqual(db.events[-1], "close")


class PersonalizationGenerationHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.user = SimpleNamespace(id=7)
        self.context = PersonalizationContext(PROMPT_BLOCK, 2, 1)

    async def _generate(self, body, *, context=None, generator=None, writer=None):
        if generator is None:
            generator = MagicMock(return_value=deepcopy(VALID_RECIPE))
        if writer is None:
            writer = MagicMock(return_value=101)
        with patch("main.get_personalization_for_request", new=AsyncMock(return_value=context)) as seam, \
                patch("main.resolve_blocks_for_request", return_value={}), \
                patch("main.call_agentic_llm", generator), \
                patch("main.compute_recipe_nutrition", return_value=STUB_NUTRITION), \
                patch("main.save_generate_history", writer), \
                patch("main.SessionLocal", return_value=MagicMock()):
            response = await main.generate_recipe_text(body, current_user=self.user, db=self.db)
        return response, seam, generator, writer

    async def test_real_frontend_base_and_custom_bodies_reach_only_the_seam(self):
        cases = (
            (request(recipe_name="Pad Kra Pao"), "Pad Kra Pao"),
            (request(recipe_name="Custom Recipe from Fridge", taste="ไม่ระบุ"), "Custom Recipe from Fridge"),
        )
        for body, expected_name in cases:
            with self.subTest(recipe=expected_name):
                _response, seam, _generator, _writer = await self._generate(body)
                seam.assert_awaited_once()
                self.assertEqual(seam.call_args.kwargs["recipe_name"], expected_name)
                self.assertEqual(seam.call_args.kwargs["ingredient_names"], ["minced pork", "holy basil"])
                self.assertEqual(seam.call_args.kwargs["taste"], body.preferences["taste"])

    async def test_retrieval_session_is_closed_before_recipe_generator(self):
        close_counts = []

        def generator(*args, **kwargs):
            close_counts.append(self.db.close.call_count)
            return deepcopy(VALID_RECIPE)

        with patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "1"}), \
                patch("main.count_embedded_signals", return_value=3), \
                patch("main.run_in_threadpool", new=AsyncMock(return_value=[[1.0] + [0.0] * 767])), \
                patch("main.build_personalization_context", return_value=self.context), \
                patch("main.resolve_blocks_for_request", return_value={}), \
                patch("main.call_agentic_llm", side_effect=generator), \
                patch("main.compute_recipe_nutrition", return_value=STUB_NUTRITION), \
                patch("main.save_generate_history", return_value=101), \
                patch("main.SessionLocal", return_value=MagicMock()):
            response = await main.generate_recipe_text(request(), current_user=self.user, db=self.db)
        self.assertEqual(response["status"], "success")
        self.assertEqual(close_counts, [3])

    async def test_success_metadata_is_actual_and_added_only_after_history_write(self):
        saved = []

        def writer(_db, _user, _request, final_output):
            saved.append(deepcopy(final_output))
            return 101

        response, _seam, generator, _writer = await self._generate(
            request(), context=self.context, writer=writer
        )
        self.assertEqual(
            response["data"]["personalization"],
            {"applied": True, "positives": 2, "negatives": 1},
        )
        self.assertNotIn("personalization", saved[0])
        llm_prefs = generator.call_args.args[1]
        self.assertEqual(llm_prefs[PERSONALIZATION_KEY], PROMPT_BLOCK)
        self.assertNotIn(PERSONALIZATION_KEY, request().preferences)
        self.assertEqual(
            set(response["data"]["personalization"]),
            {"applied", "positives", "negatives"},
        )

    async def test_cold_success_has_zeroed_metadata(self):
        response, _seam, _generator, _writer = await self._generate(request())
        self.assertEqual(
            response["data"]["personalization"],
            {"applied": False, "positives": 0, "negatives": 0},
        )

    async def test_success_logs_omit_full_recipe_response(self):
        recipe = deepcopy(VALID_RECIPE)
        recipe["safety_warning"] = "PRIVATE-RECIPE-WARNING"
        output = io.StringIO()
        with redirect_stdout(output):
            response, _seam, _generator, _writer = await self._generate(
                request(),
                context=self.context,
                generator=MagicMock(return_value=recipe),
            )

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["data"]["safety_warning"], "PRIVATE-RECIPE-WARNING")
        logs = output.getvalue()
        self.assertIn("Recipe approved", logs)
        for private_text in (
            "PRIVATE-RECIPE-WARNING",
            "Thai Basil Pork",
            VALID_RECIPE["instructions"][0],
            "<<<PERSONALIZATION_REFERENCE_DATA>>>",
            "<<<END_PERSONALIZATION_REFERENCE_DATA>>>",
        ):
            with self.subTest(private_text=private_text):
                self.assertNotIn(private_text, logs)

    async def test_client_reserved_key_never_reaches_generation_or_persistence(self):
        body = request()
        malicious = "CLIENT-CONTROLLED-PROMPT-INJECTION"
        body.preferences[PERSONALIZATION_KEY] = malicious
        persisted = []

        def writer(_db, _user, _request, final_output):
            persisted.append(deepcopy(final_output))
            return 101

        response, seam, generator, _writer = await self._generate(
            body,
            context=None,
            writer=writer,
        )

        self.assertEqual(response["status"], "success")
        self.assertEqual(
            response["data"]["personalization"],
            {"applied": False, "positives": 0, "negatives": 0},
        )
        self.assertNotIn(PERSONALIZATION_KEY, seam.call_args.kwargs["user_prefs"])
        self.assertNotIn(PERSONALIZATION_KEY, generator.call_args.args[1])
        self.assertEqual(body.preferences[PERSONALIZATION_KEY], malicious)
        self.assertNotIn(malicious, json.dumps(response, ensure_ascii=False))
        self.assertNotIn(malicious, json.dumps(persisted, ensure_ascii=False))

    async def test_generation_error_contract_is_unchanged(self):
        generator = MagicMock(return_value={"error": "no key"})
        response, _seam, _generator, writer = await self._generate(
            request(), context=self.context, generator=generator
        )
        self.assertEqual(response, {"status": "error", "message": "no key"})
        writer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
