# backend/tests/test_local_generator.py
import json
import os
import unittest
from unittest.mock import Mock, patch

from generators.local_generator import LocalLLMGenerator
from test_recipe_instructions import wire_recipe, SELECTED
from recipe_instructions import FORMAT_ERROR, generation_schema, normalize_generated_recipe


def make_response(payload, status_code=200):
    resp = Mock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.raise_for_status = Mock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


class LocalLLMGeneratorTests(unittest.TestCase):
    def test_generate_returns_parsed_json_on_success(self):
        fake_recipe = wire_recipe()
        openai_style_response = {
            "choices": [{"message": {"content": json.dumps(fake_recipe)}}]
        }
        gen = LocalLLMGenerator(base_url="http://localhost:8001", model="qwen2.5-7b-instruct")
        with patch("generators.local_generator.requests.post", return_value=make_response(openai_style_response)) as mock_post:
            result = gen.generate(SELECTED, {}, {"name": "base"})

        self.assertEqual(result, normalize_generated_recipe(fake_recipe, SELECTED))
        self.assertEqual(result["estimated_total_time"], {"min_minutes": 5, "max_minutes": 10})
        self.assertEqual(mock_post.call_args.kwargs["json"]["response_format"]["json_schema"]["schema"], generation_schema(SELECTED))
        called_url = mock_post.call_args.args[0]
        self.assertEqual(called_url, "http://localhost:8001/v1/chat/completions")
        sent_model = mock_post.call_args.kwargs["json"]["model"]
        self.assertEqual(sent_model, "qwen2.5-7b-instruct")

    def test_generate_passes_feedback_into_prompt(self):
        response_payload = {"choices": [{"message": {"content": "{}"}}]}
        gen = LocalLLMGenerator(base_url="http://localhost:8001", model="qwen2.5-4b-instruct")
        with patch("generators.local_generator.requests.post", return_value=make_response(response_payload)) as mock_post:
            gen.generate(["egg"], {}, {"name": "base"}, feedback="Invalid diet tags")

        sent_messages = mock_post.call_args.kwargs["json"]["messages"]
        self.assertIn("Invalid diet tags", sent_messages[0]["content"])

    @patch.dict(os.environ, {"LOCAL_LLM_BASE_URL": "", "LOCAL_LLM_MODEL": ""})
    def test_generate_returns_error_dict_when_base_url_missing(self):
        # Hermetic on purpose (Task 3's lesson): explicitly clear the env
        # vars the constructor falls back to AND patch requests.post so this
        # test can never make a real network call, regardless of whatever
        # LOCAL_LLM_BASE_URL/LOCAL_LLM_MODEL happen to be set to in whatever
        # environment runs this suite.
        gen = LocalLLMGenerator(base_url=None, model="qwen2.5-7b-instruct")
        with patch("generators.local_generator.requests.post") as mock_post:
            result = gen.generate(["egg"], {}, {"name": "base"})

        mock_post.assert_not_called()
        self.assertIn("error", result)

    def test_generate_returns_error_dict_on_request_exception(self):
        gen = LocalLLMGenerator(base_url="http://localhost:8001", model="qwen2.5-7b-instruct")
        with patch("generators.local_generator.requests.post", side_effect=ConnectionError("refused")):
            result = gen.generate(["egg"], {}, {"name": "base"})

        self.assertIn("error", result)
        self.assertIn("refused", result["details"])

    def test_generate_returns_error_dict_on_non_json_content(self):
        response_payload = {"choices": [{"message": {"content": "not json"}}]}
        gen = LocalLLMGenerator(base_url="http://localhost:8001", model="qwen2.5-7b-instruct")
        with patch("generators.local_generator.requests.post", return_value=make_response(response_payload)):
            result = gen.generate(["egg"], {}, {"name": "base"})

        self.assertIn(FORMAT_ERROR, result)

    def test_response_is_validated_even_when_server_ignores_schema(self):
        for change in ({"safety_warning": "ระวัง 开"}, {"instructions": ["คลุกผักแล้วเติมทุเรียน"]}):
            raw = {**wire_recipe(), **change}
            response = {"choices": [{"message": {"content": json.dumps(raw, ensure_ascii=False)}}]}
            gen = LocalLLMGenerator(base_url="http://localhost:8001", model="mock")
            with self.subTest(change=change), patch("generators.local_generator.requests.post", return_value=make_response(response)):
                self.assertIn(FORMAT_ERROR, gen.generate(SELECTED, {}, {}))


if __name__ == "__main__":
    unittest.main()
