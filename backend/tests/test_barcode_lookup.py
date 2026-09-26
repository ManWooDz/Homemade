import os
import sys
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from auth import get_current_user
from database.models import User
from main import app, _map_off_nutrition


class BarcodeLookupTests(unittest.TestCase):
    def setUp(self):
        fake_user = User(id=1, email="user@example.com", hashed_password="x")
        app.dependency_overrides[get_current_user] = lambda: fake_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_invalid_code_format_rejected_without_network_call(self):
        with patch("main.requests.get") as mock_get:
            res = self.client.get("/api/barcode-lookup", params={"code": "../../etc"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "error")
        mock_get.assert_not_called()

    def test_product_found_maps_fields(self):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "status": 1,
            "product": {
                "product_name_th": "นมสด",
                "categories_tags": ["en:dairies", "en:milks"],
                "image_front_url": "https://example.com/milk.jpg",
            },
        }
        with patch("main.requests.get", return_value=mock_response) as mock_get:
            res = self.client.get("/api/barcode-lookup", params={"code": "8850999327015"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["data"]["name"], "นมสด")
        self.assertEqual(body["data"]["category"], "Other")
        self.assertEqual(body["data"]["image"], "https://example.com/milk.jpg")
        mock_get.assert_called_once()
        self.assertIn("User-Agent", mock_get.call_args.kwargs["headers"])

    def test_product_not_found_returns_error(self):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"status": 0}
        with patch("main.requests.get", return_value=mock_response):
            res = self.client.get("/api/barcode-lookup", params={"code": "00000000"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "error")

    def test_network_timeout_returns_error_not_500(self):
        import requests as real_requests

        with patch("main.requests.get", side_effect=real_requests.Timeout("timed out")):
            res = self.client.get("/api/barcode-lookup", params={"code": "8850999327015"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "error")

    def test_meat_category_keyword_maps_correctly(self):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "status": 1,
            "product": {
                "product_name": "Chicken Breast",
                "categories_tags": ["en:meats", "en:poultry"],
                "image_front_url": "",
            },
        }
        with patch("main.requests.get", return_value=mock_response):
            res = self.client.get("/api/barcode-lookup", params={"code": "8850999327015"})
        self.assertEqual(res.json()["data"]["category"], "Meat & poultry")

    def test_product_with_full_nutriments_maps_all_macros(self):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "status": 1,
            "product": {
                "product_name": "Cola",
                "categories_tags": [],
                "image_front_url": "",
                "nutriments": {
                    "energy-kcal_100g": 42,
                    "proteins_100g": 0,
                    "carbohydrates_100g": 10.6,
                    "fat_100g": 0,
                },
            },
        }
        with patch("main.requests.get", return_value=mock_response):
            res = self.client.get("/api/barcode-lookup", params={"code": "8850999327015"})
        nutrition = res.json()["data"]["nutrition_data"]
        self.assertEqual(
            nutrition,
            {"basis": "per_100g_or_ml", "calories": 42.0, "protein_g": 0.0, "carbs_g": 10.6, "fat_g": 0.0},
        )

    def test_product_with_no_nutriments_has_null_nutrition_data(self):
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "status": 1,
            "product": {"product_name": "Mystery Item", "categories_tags": [], "image_front_url": ""},
        }
        with patch("main.requests.get", return_value=mock_response):
            res = self.client.get("/api/barcode-lookup", params={"code": "8850999327015"})
        self.assertIsNone(res.json()["data"]["nutrition_data"])


class MapOffNutritionUnitTests(unittest.TestCase):
    def test_partial_data_keeps_missing_macros_as_none(self):
        result = _map_off_nutrition({"energy-kcal_100g": 100})
        self.assertEqual(result, {"basis": "per_100g_or_ml", "calories": 100.0, "protein_g": None, "carbs_g": None, "fat_g": None})

    def test_no_calorie_figure_at_all_returns_none(self):
        result = _map_off_nutrition({"proteins_100g": 5})
        self.assertIsNone(result)

    def test_empty_nutriments_returns_none(self):
        self.assertIsNone(_map_off_nutrition({}))
        self.assertIsNone(_map_off_nutrition(None))

    def test_non_numeric_value_becomes_none_for_that_field_not_a_crash(self):
        result = _map_off_nutrition({"energy-kcal_100g": 50, "proteins_100g": "not-a-number"})
        self.assertEqual(result["calories"], 50.0)
        self.assertIsNone(result["protein_g"])

    def test_kj_fallback_used_when_kcal_missing(self):
        # 180 kJ / 4.184 = 43.0 kcal
        result = _map_off_nutrition({"energy-kj_100g": 180})
        self.assertEqual(result["calories"], 43.0)

    def test_generic_energy_field_used_as_kj_fallback_when_no_explicit_kj_key(self):
        result = _map_off_nutrition({"energy_100g": 180})
        self.assertEqual(result["calories"], 43.0)

    def test_kcal_takes_priority_over_kj_when_both_present(self):
        result = _map_off_nutrition({"energy-kcal_100g": 42, "energy-kj_100g": 999})
        self.assertEqual(result["calories"], 42.0)


if __name__ == "__main__":
    unittest.main()
