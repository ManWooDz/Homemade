import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from google.genai import errors
from gemini_keys import create_client


class GeminiKeyTests(unittest.TestCase):
    def test_free_success_and_quota_fallback_then_free_again(self):
        free = Mock()
        paid = Mock()
        quota = errors.ClientError(429, {"error": {"status": "RESOURCE_EXHAUSTED"}})
        free.models.generate_content.side_effect = [quota, "free result"]
        paid.models.generate_content.return_value = "paid result"
        with patch.dict(os.environ, {"GEMINI_API_KEY_FREE": "synthetic-free", "GEMINI_API_KEY": "synthetic-paid"}), patch("gemini_keys.genai.Client", side_effect=[free, paid]) as factory:
            client = create_client()
            self.assertEqual(client.models.generate_content(model="model", contents="recipe"), "paid result")
            self.assertEqual(client.models.generate_content(model="model", contents="recipe"), "free result")
            self.assertEqual(factory.call_count, 2)
            self.assertEqual(factory.call_args_list[0].kwargs["api_key"], "synthetic-free")
            for call in factory.call_args_list:
                self.assertEqual(call.kwargs["http_options"].retry_options.attempts, 1)
            paid.models.generate_content.assert_called_once_with(model="model", contents="recipe")

    def test_non_quota_errors_never_use_paid_key(self):
        for failure in [errors.ClientError(code, {}) for code in (400, 401, 403)] + [errors.ServerError(503, {}), TimeoutError(), ValueError("bad data")]:
            free = Mock()
            free.models.generate_content.side_effect = failure
            with self.subTest(failure=type(failure).__name__), patch.dict(os.environ, {"GEMINI_API_KEY_FREE": "free", "GEMINI_API_KEY": "paid"}), patch("gemini_keys.genai.Client", return_value=free) as factory:
                with self.assertRaises(type(failure)):
                    create_client().models.generate_content(model="model")
                self.assertEqual(factory.call_count, 1)

    def test_missing_duplicate_and_explicit_keys(self):
        for free, paid, explicit, expected in [("", "paid", None, "paid"), ("free", "paid", "override", "override"), ("free", "free", None, "free"), ("", "", None, None), ("free", "paid", "", None)]:
            with self.subTest(free=free, explicit=explicit), patch.dict(os.environ, {"GEMINI_API_KEY_FREE": free, "GEMINI_API_KEY": paid}), patch("gemini_keys.genai.Client") as factory:
                client = create_client(api_key=explicit)
                if expected:
                    self.assertIsNotNone(client)
                    self.assertEqual(factory.call_args.kwargs["api_key"], expected)
                else:
                    self.assertIsNone(client)
                    factory.assert_not_called()

    def test_embedding_timeout_payload_and_paid_failure_propagate_without_loop(self):
        free, paid = Mock(), Mock()
        free.models.embed_content.side_effect = errors.ClientError(429, {})
        paid.models.embed_content.side_effect = errors.ClientError(429, {})
        config = object()
        with patch.dict(os.environ, {"GEMINI_API_KEY_FREE": "free", "GEMINI_API_KEY": "paid"}), patch("gemini_keys.genai.Client", side_effect=[free, paid]) as factory:
            client = create_client(timeout=5000)
            with self.assertRaises(errors.ClientError):
                client.models.embed_content(model="embedding", contents=["text"], config=config)
            self.assertEqual(factory.call_count, 2)
            self.assertEqual(factory.call_args.kwargs["http_options"].timeout, 5000)
            paid.models.embed_content.assert_called_once_with(model="embedding", contents=["text"], config=config)

    def test_free_only_quota_is_not_retried(self):
        free = Mock()
        free.models.generate_content.side_effect = errors.ClientError(429, {})
        with patch.dict(os.environ, {"GEMINI_API_KEY_FREE": "free", "GEMINI_API_KEY": ""}), patch("gemini_keys.genai.Client", return_value=free) as factory:
            with self.assertRaises(errors.ClientError):
                create_client().models.generate_content(model="model")
            self.assertEqual(factory.call_count, 1)

    def test_all_four_callers_use_the_same_routing_without_payload_changes(self):
        import main
        from embeddings import embed_request_queries
        from generators.gemini_generator import GeminiGenerator
        from nutrition.llm_fallback import NutritionLLMEstimator
        from test_recipe_instructions import SELECTED, wire_recipe
        for caller in ("production", "benchmark", "nutrition", "embedding"):
            free, paid = Mock(), Mock()
            method = "embed_content" if caller == "embedding" else "generate_content"
            getattr(free.models, method).side_effect = errors.ClientError(429, {})
            if caller == "embedding":
                response = SimpleNamespace(embeddings=[SimpleNamespace(values=[1.] + [0.] * 767)])
            elif caller == "nutrition":
                response = SimpleNamespace(text=json.dumps([{"calories": 10, "protein_g": 1, "carbs_g": 1, "fat_g": 1}]))
            else:
                response = SimpleNamespace(text=json.dumps(wire_recipe(), ensure_ascii=False))
            getattr(paid.models, method).return_value = response
            with self.subTest(caller=caller), patch.dict(os.environ, {"GEMINI_API_KEY_FREE": "synthetic-free", "GEMINI_API_KEY": "synthetic-paid"}), patch("gemini_keys.genai.Client", side_effect=[free, paid]), self.assertLogs("gemini_keys", level="INFO") as logs:
                if caller == "production":
                    with patch("main.client", create_client()):
                        result = main.call_agentic_llm(SELECTED, {}, {})
                    self.assertIn("instructions", result)
                elif caller == "benchmark":
                    result = GeminiGenerator().generate(SELECTED, {}, {})
                    self.assertIn("instructions", result)
                elif caller == "nutrition":
                    self.assertEqual(NutritionLLMEstimator().estimate(["food"])[0].calories, 10)
                else:
                    self.assertEqual(len(embed_request_queries(["query"])[0]), 768)
                self.assertEqual(getattr(free.models, method).call_args, getattr(paid.models, method).call_args)
                self.assertEqual(getattr(paid.models, method).call_count, 1)
                self.assertNotIn("synthetic-free", " ".join(logs.output))
                self.assertNotIn("synthetic-paid", " ".join(logs.output))
