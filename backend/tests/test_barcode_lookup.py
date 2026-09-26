import os
import sys
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from auth import get_current_user
from database.models import User
from main import app


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


if __name__ == "__main__":
    unittest.main()
