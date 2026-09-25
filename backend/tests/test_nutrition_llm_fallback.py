import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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
        estimator._client = "must not be used"
        self.assertEqual(estimator.estimate([]), [])

    @patch.dict(os.environ, {"GEMINI_API_KEY": ""})
    def test_no_api_key_returns_all_none_macros(self):
        estimator = NutritionLLMEstimator(api_key=None)
        result = estimator.estimate(["ใบมะกรูด"])
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0].calories)


if __name__ == "__main__":
    unittest.main()
