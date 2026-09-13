# backend/tests/test_gemini_generator.py
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from generators.gemini_generator import GeminiGenerator


class GeminiGeneratorTests(unittest.TestCase):
    def test_generate_returns_parsed_json_on_success(self):
        fake_recipe = {"recipe_name": "Thai Basil Pork", "servings": 2}

        def fake_generate_content(**kwargs):
            return SimpleNamespace(text=json.dumps(fake_recipe))

        fake_client = SimpleNamespace(
            models=SimpleNamespace(generate_content=fake_generate_content)
        )
        gen = GeminiGenerator(api_key="fake-key")
        with patch.object(gen, "_client", fake_client):
            result = gen.generate(["pork"], {}, {"name": "base"})

        self.assertEqual(result, fake_recipe)

    def test_generate_passes_feedback_into_prompt(self):
        captured = {}

        def fake_generate_content(**kwargs):
            captured["prompt"] = kwargs["contents"]
            return SimpleNamespace(text="{}")

        fake_client = SimpleNamespace(
            models=SimpleNamespace(generate_content=fake_generate_content)
        )
        gen = GeminiGenerator(api_key="fake-key")
        with patch.object(gen, "_client", fake_client):
            gen.generate(["pork"], {}, {"name": "base"}, feedback="Invalid nutrition value: fat_g")

        self.assertIn("Invalid nutrition value: fat_g", captured["prompt"])

    @patch.dict(os.environ, {"GEMINI_API_KEY": ""})
    def test_generate_returns_error_dict_when_no_api_key(self):
        # This worktree's backend/.env has a real GEMINI_API_KEY (gitignored,
        # environment-local). GeminiGenerator(api_key=None) falls back to
        # os.getenv("GEMINI_API_KEY") by design (mirrors main.py's own
        # module-level fallback), so without isolating the env here this
        # test would construct a real client and hit the live Gemini API
        # instead of exercising the "no key" path it's named for.
        gen = GeminiGenerator(api_key=None)
        result = gen.generate(["pork"], {}, {"name": "base"})
        self.assertIn("error", result)

    def test_generate_returns_error_dict_on_exception(self):
        def raise_error(**kwargs):
            raise RuntimeError("network down")

        fake_client = SimpleNamespace(
            models=SimpleNamespace(generate_content=raise_error)
        )
        gen = GeminiGenerator(api_key="fake-key")
        with patch.object(gen, "_client", fake_client):
            result = gen.generate(["pork"], {}, {"name": "base"})

        self.assertIn("error", result)
        self.assertIn("network down", result["details"])


if __name__ == "__main__":
    unittest.main()
