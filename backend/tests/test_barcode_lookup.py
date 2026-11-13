import json
import os
import sys
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from auth import get_current_user
import barcode_nutrition
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


class BarcodeProductLabelTests(unittest.TestCase):
    CODE = "0034000470693"
    provider = barcode_nutrition

    @staticmethod
    def label(*, per="100ml", calories=120, source="packaging", **fields):
        return {
            "source": source,
            "preparation": "as_sold",
            "per": per,
            "nutrients": {
                "energy-kcal": {"value": calories, "unit": "kcal"},
                "proteins": {"value": 2000, "unit": "mg"},
                "carbohydrates-total": {"value": 8, "unit": "g"},
                "fat": {"value": 0, "unit": "g"},
            },
            **fields,
        }

    def binding(self, *sets, product_code=None, request_code="034000470693"):
        response = Mock()
        response.json.return_value = {
            "status": "success",
            "product": {
                "code": self.CODE if product_code is None else product_code,
                "product_name_th": "นมสด",
                "nutrition": {
                    "input_sets": list(sets),
                    "aggregated_set": self.label(source="estimate"),
                },
            },
        }
        with patch.object(self.provider.requests, "get", return_value=response) as get:
            binding = self.provider.load_barcode_binding(request_code)
        self.assertIn(f"/api/v3.5/product/{self.CODE}", get.call_args.args[0])
        self.assertIn("nutrition", get.call_args.kwargs["params"]["fields"])
        self.assertGreater(get.call_args.kwargs["timeout"], 0)
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        return binding

    def test_explicit_per_serving_basis_normalizes_one_label_and_calculates(self):
        label = self.label(per="serving", per_quantity=30, per_unit="g")
        label["nutrients"].pop("energy-kcal")
        label["nutrients"]["energy-kj"] = {"value": 418.4, "unit": "kJ"}
        binding = self.binding(label)
        self.assertEqual((binding["barcode"], binding["product_name"]), (self.CODE, "นมสด"))
        normalized, = binding["sets"]
        self.assertEqual(normalized["label_source"], "packaging")
        self.assertEqual(normalized["basis"], {"quantity": 30, "unit": "g"})
        self.assertEqual(normalized["carbohydrate_kind"], "total")
        for key, expected in {"calories": 100, "protein_g": 2, "carbs_g": 8, "fat_g": 0}.items():
            self.assertAlmostEqual(normalized["macros"][key], expected)
        trace, reason = self.provider.product_contribution(binding, 15, "กรัม")
        self.assertIsNone(reason)
        self.assertEqual(trace["basis"], {"quantity": 30, "unit": "g"})
        self.assertEqual(trace["converted_quantity"], {"amount": 15, "unit": "g"})
        for key, expected in {"calories": 50, "protein_g": 1, "carbs_g": 4, "fat_g": 0}.items():
            self.assertAlmostEqual(trace["contribution"][key], expected)
        self.assertEqual(trace["method"], "direct_mass")

    def test_direct_volume_uses_native_volume(self):
        trace, reason = self.provider.product_contribution(self.binding(self.label()), 2, "ช้อนโต๊ะ")
        self.assertIsNone(reason)
        self.assertEqual(trace["source"], "product_label")
        self.assertEqual(trace["label_source"], "packaging")
        self.assertEqual(trace["carbohydrate_kind"], "total")
        self.assertEqual(trace["converted_quantity"], {"amount": 30, "unit": "ml"})
        self.assertEqual(trace["method"], "direct_volume")
        self.assertAlmostEqual(trace["contribution"]["calories"], 36)

    def test_available_carbohydrates_do_not_supply_total_carbohydrates(self):
        label = self.label()
        label["nutrients"]["carbohydrates"] = label["nutrients"].pop("carbohydrates-total")
        binding = self.binding(label)
        self.assertEqual(binding["sets"][0]["carbohydrate_kind"], "available")
        self.assertIsNone(binding["sets"][0]["macros"]["carbs_g"])
        self.assertEqual(self.provider.product_contribution(binding, 30, "มล."), (None, "product_label_incomplete"))
        self.assertIsNone(self.provider.product_display_nutrition(binding))

    def test_only_complete_as_sold_input_sets_are_usable(self):
        label = self.label()
        label["nutrients"]["fat"]["modifier"] = "<"
        binding = self.binding(label, self.label(preparation="prepared"), self.label(source="usda"))
        self.assertEqual(len(binding["sets"]), 1)
        self.assertIsNone(binding["sets"][0]["macros"]["fat_g"])
        self.assertEqual(self.provider.product_contribution(binding, 30, "มล."), (None, "product_label_incomplete"))

    def test_unqualified_bases_and_aggregated_values_are_unavailable(self):
        binding = self.binding(
            self.label(per="serving", per_quantity=0, per_unit="g"),
            self.label(per="100ml", per_quantity=100, per_unit="g"),
            self.label(per="serving", per_quantity=2, per_unit="pack"),
        )
        self.assertEqual(binding["sets"], [])
        self.assertEqual(self.provider.product_contribution(binding, 30, "มล."), (None, "product_label_unavailable"))

    def test_duplicate_equivalent_label_sets_work_and_conflicting_labels_fall_back(self):
        equivalent = self.label(per="serving", per_quantity=50, per_unit="ml", calories=60, source="manufacturer")
        for nutrient in ("proteins", "carbohydrates-total", "fat"):
            equivalent["nutrients"][nutrient]["value"] /= 2
        binding = self.binding(self.label(), equivalent)
        trace, reason = self.provider.product_contribution(binding, 100, "มล.")
        self.assertIsNone(reason)
        self.assertEqual(trace["contribution"]["calories"], 120)
        self.assertEqual(self.provider.product_display_nutrition(binding), {
            "basis": "per_100g_or_ml", "calories": 120, "protein_g": 2, "carbs_g": 8, "fat_g": 0,
        })
        conflict = self.binding(self.label(), self.label(calories=130, source="manufacturer"))
        self.assertEqual(self.provider.product_contribution(conflict, 100, "มล."), (None, "product_label_conflict"))
        self.assertIsNone(self.provider.product_display_nutrition(conflict))

    def test_only_a_reviewed_same_product_pair_can_bridge_mass_and_volume(self):
        binding = self.binding(self.label())
        contribution = self.provider.product_contribution
        self.assertEqual(contribution(binding, 130, "กรัม"), (None, "product_conversion_unavailable"))
        self.assertEqual(contribution(binding, 2, "ขวด"), (None, "product_quantity_unresolved"))
        pair = {
            "barcode": self.CODE, "preparation": "as_sold", "grams": 260, "milliliters": 250,
            "source_url": "https://example.com/manufacturer/serving",
        }
        with patch.object(self.provider, "_PRODUCT_CONVERSIONS_PATH") as catalog:
            catalog.read_text.return_value = json.dumps([pair])
            trace, reason = contribution(binding, 130, "กรัม")
            self.assertIsNone(reason)
            self.assertEqual(trace["converted_quantity"], {"amount": 125, "unit": "ml"})
            self.assertEqual(trace["contribution"]["calories"], 150)
            self.assertEqual(trace["conversion_evidence"], pair)
            self.assertEqual(trace["method"], "reviewed_product_conversion")
            direct, reason = contribution(self.binding(self.label(), self.label(per="100g", calories=135)), 100, "กรัม")
            self.assertIsNone(reason)
            self.assertEqual(direct["contribution"]["calories"], 135)
            self.assertNotIn("conversion_evidence", direct)
            catalog.read_text.return_value = json.dumps([pair, {**pair, "grams": 200}])
            self.assertEqual(contribution(binding, 130, "กรัม"), (None, "product_conversion_unavailable"))

    def test_lookup_rejects_mismatched_identity_and_transport_failure(self):
        with self.assertRaises(self.provider.BarcodeNutritionLookupError):
            self.binding(self.label(), product_code="0034000470694")
        with patch.object(self.provider.requests, "get", side_effect=self.provider.requests.Timeout):
            with self.assertRaises(self.provider.BarcodeNutritionLookupError):
                self.provider.load_barcode_binding(self.CODE)
        with patch.object(self.provider.requests, "get") as get:
            with self.assertRaises(self.provider.BarcodeNutritionLookupError):
                self.provider.load_barcode_binding("１２３４５６７８")
            get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
