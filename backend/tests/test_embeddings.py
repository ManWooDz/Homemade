import math
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from embeddings import (
    EmbeddingError,
    build_history_document,
    build_request_query,
    embed_history_documents,
    embed_request_queries,
)


def _response_for(*vectors):
    return SimpleNamespace(
        embeddings=[SimpleNamespace(values=vector) for vector in vectors]
    )


class EmbeddingTextBuilderTests(unittest.TestCase):
    def test_history_document_uses_parser_names_and_stable_deduplication(self):
        result = build_history_document(
            "Thai Basil Pork",
            ["หมูสับ 200 กรัม", "ใบกะเพรา 1 กำ", "หมูสับ 100 กรัม", "  "],
            ["Thai", "Spicy", "thai", ""],
        )

        self.assertEqual(
            result,
            "Thai Basil Pork | วัตถุดิบ: หมูสับ, ใบกะเพรา | diet_tags: Thai, Spicy",
        )

    def test_history_document_omits_blank_sections(self):
        self.assertEqual(build_history_document("Pad Thai", ["  "], [" "]), "Pad Thai")

    def test_request_query_omits_custom_recipe_title(self):
        self.assertEqual(
            build_request_query("Custom Recipe from Fridge", ["หมูสับ", "ใบกะเพรา"], "เผ็ด"),
            "วัตถุดิบ: หมูสับ, ใบกะเพรา | taste: เผ็ด",
        )

    def test_request_query_omits_unspecified_taste(self):
        self.assertEqual(
            build_request_query("Custom Recipe", ["rice", "egg"], "ไม่ระบุ"),
            "วัตถุดิบ: rice, egg",
        )

    def test_request_query_keeps_real_base_title_and_deduplicates_ingredients(self):
        self.assertEqual(
            build_request_query("Pad Thai", ["rice", "egg", "rice", "  "], "sweet"),
            "Pad Thai | วัตถุดิบ: rice, egg | taste: sweet",
        )

    def test_request_query_returns_empty_string_when_every_section_is_blank(self):
        self.assertEqual(build_request_query("Custom Recipe", [" "], " "), "")


class EmbeddingTests(unittest.TestCase):
    def _client_with_response(self, response):
        captured = {}

        def embed_content(**kwargs):
            captured.update(kwargs)
            return response

        return SimpleNamespace(models=SimpleNamespace(embed_content=embed_content)), captured

    def test_history_embeddings_use_document_task_and_manual_l2_normalization(self):
        vector = [3.0, 4.0] + [0.0] * 766
        client, captured = self._client_with_response(_response_for(vector))

        result = embed_history_documents(["history document"], client=client)

        self.assertEqual(captured["model"], "gemini-embedding-001")
        self.assertEqual(captured["contents"], ["history document"])
        self.assertEqual(captured["config"].task_type, "RETRIEVAL_DOCUMENT")
        self.assertEqual(captured["config"].output_dimensionality, 768)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0][0], 0.6)
        self.assertAlmostEqual(result[0][1], 0.8)
        self.assertAlmostEqual(math.sqrt(sum(value * value for value in result[0])), 1.0)

    def test_request_embeddings_use_query_task(self):
        vector = [1.0] + [0.0] * 767
        client, captured = self._client_with_response(_response_for(vector))

        result = embed_request_queries(["request query"], client=client)

        self.assertEqual(captured["model"], "gemini-embedding-001")
        self.assertEqual(captured["contents"], ["request query"])
        self.assertEqual(captured["config"].task_type, "RETRIEVAL_QUERY")
        self.assertEqual(captured["config"].output_dimensionality, 768)
        self.assertEqual(result, [vector])

    def test_embedding_rejects_response_with_wrong_count(self):
        vector = [1.0] + [0.0] * 767
        client, _ = self._client_with_response(_response_for(vector))

        with self.assertRaises(EmbeddingError):
            embed_request_queries(["one", "two"], client=client)

    def test_embedding_rejects_response_with_wrong_dimension(self):
        client, _ = self._client_with_response(_response_for([1.0] * 767))

        with self.assertRaises(EmbeddingError):
            embed_request_queries(["query"], client=client)

    def test_embedding_rejects_non_finite_components(self):
        for invalid_value in (float("nan"), float("inf")):
            with self.subTest(invalid_value=invalid_value):
                vector = [1.0] + [0.0] * 766 + [invalid_value]
                client, _ = self._client_with_response(_response_for(vector))

                with self.assertRaises(EmbeddingError):
                    embed_history_documents(["document"], client=client)

    def test_embedding_rejects_zero_norm(self):
        client, _ = self._client_with_response(_response_for([0.0] * 768))

        with self.assertRaises(EmbeddingError):
            embed_history_documents(["document"], client=client)

    @patch.dict(os.environ, {"GEMINI_API_KEY": ""})
    def test_embedding_rejects_missing_api_key_when_client_is_not_injected(self):
        with self.assertRaises(EmbeddingError):
            embed_history_documents(["document"])

    def test_embedding_wraps_sdk_exception(self):
        def raise_sdk_error(**kwargs):
            raise RuntimeError("SDK unavailable")

        client = SimpleNamespace(models=SimpleNamespace(embed_content=raise_sdk_error))

        with self.assertRaises(EmbeddingError):
            embed_request_queries(["query"], client=client)

    @patch("embeddings.genai.Client")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_embedding_constructs_client_with_bounded_http_options(self, client_constructor):
        vector = [1.0] + [0.0] * 767
        client_constructor.return_value = SimpleNamespace(
            models=SimpleNamespace(embed_content=lambda **kwargs: _response_for(vector))
        )

        embed_request_queries(["query"])

        client_constructor.assert_called_once()
        self.assertEqual(client_constructor.call_args.kwargs["api_key"], "test-key")
        http_options = client_constructor.call_args.kwargs["http_options"]
        self.assertEqual(http_options.timeout, 5000)
        self.assertEqual(http_options.retry_options.attempts, 1)


if __name__ == "__main__":
    unittest.main()
