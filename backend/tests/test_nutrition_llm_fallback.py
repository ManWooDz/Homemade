import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from nutrition.llm_fallback import NutritionLLMEstimator


class NutritionLLMEstimatorTests(unittest.TestCase):
    def test_estimate_returns_macro_values_in_order(self):
        fake_payload = [
            {"calories": 50.0, "protein_g": 1.0, "carbs_g": 10.0, "fat_g": 0.2},
            {"calories": 300.0, "protein_g": 25.0, "carbs_g": 0.0, "fat_g": 22.0},
        ]

        def fake_generate_content(**kwargs):
            return SimpleNamespace(text=json.dumps(fake_payload))

        fake_client = SimpleNamespace(models=SimpleNamespace(generate_content=fake_generate_content))
        estimator = NutritionLLMEstimator(api_key="fake-key")
        with patch.object(estimator, "_client", fake_client):
            result = estimator.estimate(["ใบมะกรูด", "หมูสามชั้น"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].calories, 50.0)
        self.assertEqual(result[1].protein_g, 25.0)

    def test_empty_input_makes_no_call(self):
        estimator = NutritionLLMEstimator(api_key="fake-key")
        estimator._client = MagicMock()
        result = estimator.estimate([])
        self.assertEqual(result, [])
        estimator._client.models.generate_content.assert_not_called()

    @patch.dict(os.environ, {"GEMINI_API_KEY": ""})
    def test_no_api_key_returns_all_none_macros(self):
        estimator = NutritionLLMEstimator(api_key=None)
        result = estimator.estimate(["ใบมะกรูด"])
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0].calories)

    def test_length_mismatch_returns_all_none_macros(self):
        """If LLM returns different number of items than requested, return all-None."""
        fake_payload = [
            {"calories": 50.0, "protein_g": 1.0, "carbs_g": 10.0, "fat_g": 0.2},
        ]

        def fake_generate_content(**kwargs):
            return SimpleNamespace(text=json.dumps(fake_payload))

        fake_client = SimpleNamespace(models=SimpleNamespace(generate_content=fake_generate_content))
        estimator = NutritionLLMEstimator(api_key="fake-key")
        with patch.object(estimator, "_client", fake_client):
            result = estimator.estimate(["ใบมะกรูด", "หมูสามชั้น"])
        self.assertEqual(len(result), 2)
        self.assertIsNone(result[0].calories)
        self.assertIsNone(result[1].calories)


if __name__ == "__main__":
    unittest.main()
