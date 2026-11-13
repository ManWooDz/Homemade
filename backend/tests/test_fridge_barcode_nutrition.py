from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

from database.models import Base, IngredientNutrition, IngredientNutritionAlias, UserIngredient
from test_history_endpoints import GENERATED, HistoryEndpointTestCase


BARCODE = "8859568700769"
LABEL = {
    "barcode": BARCODE,
    "product_name": "Minced pork A",
    "sets": [{
        "label_source": "packaging",
        "carbohydrate_kind": "total",
        "basis": {"quantity": 100, "unit": "g"},
        "macros": {"calories": 120, "protein_g": 12, "carbs_g": 3, "fat_g": 5},
    }],
}


class FridgeBarcodeNutritionTests(HistoryEndpointTestCase):
    def setUp(self):
        super().setUp()
        Base.metadata.create_all(self.engine, tables=[
            UserIngredient.__table__, IngredientNutrition.__table__, IngredientNutritionAlias.__table__,
        ])
        self.alice = self.login("barcode-alice@example.com")
        with self.session_local() as db:
            generic = IngredientNutrition(
                ingredient_name="minced pork", source="INMU", source_ref="test-pork", unit_basis="100g",
                calories=80, protein_g=8, carbs_g=2, fat_g=4,
            )
            db.add(generic)
            db.flush()
            db.add(IngredientNutritionAlias(alias="หมูสับ", ingredient_nutrition_id=generic.id))
            db.commit()

    def create_item(self, *, barcode=BARCODE, label=LABEL, name="หมูสับ"):
        payload = {"name": name, "quantity_amount": 700, "quantity_unit": "กรัม",
                   "nutrition_data": {"basis": "per_100g_or_ml", "calories": 999}}
        if barcode is not None:
            payload["barcode_code"] = barcode
        with patch("main.load_barcode_binding", return_value=deepcopy(label)):
            response = self.alice.post("/api/user-ingredients", json=payload, headers=self.origin)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def selection(self, row):
        return {"name": row["name"], "id": "ui-only", "fridge_ingredient_id": row["id"],
                "fridge_binding_revision": row.get("barcode_product", {}).get("revision")}

    def update_item(self, row, *, name="หมูสับ", **fields):
        return self.alice.put(f'/api/user-ingredients/{row["id"]}', headers=self.origin, json={
            "name": name, "category": "Other", "expiry_date": None, "quantity_amount": 2,
            "quantity_unit": "กรัม", **fields,
        })

    def generate(self, ingredients, *, client=None, adapted=False):
        body = {
            "recipe": {"name": "Holy Basil Pork" if adapted else "Custom Recipe from Fridge"},
            "ingredients": [*ingredients, {"name": "holy basil leaves"}],
            "preferences": {"allergy": "", "taste": "", "equipment": "", "extra": ""},
        }
        estimator = MagicMock()
        estimator.estimate.return_value = []
        with patch("main.call_agentic_llm", return_value=deepcopy(GENERATED)) as generator, \
                patch("main.NutritionLLMEstimator", return_value=estimator), \
                patch("main.get_personalization_for_request", new=AsyncMock(return_value=None)), \
                patch("main.SessionLocal", self.session_local):
            result = (client or self.alice).post("/api/generate-recipe-text", json=body, headers=self.origin)
        self.assertEqual(result.status_code, 200, result.text)
        return result.json(), generator

    def test_confirmed_product_precedes_generic_and_history_keeps_original_evidence(self):
        row = self.create_item()
        self.assertEqual(row.get("barcode_product", {}).get("barcode"), BARCODE)
        selection = self.selection(row)
        self.assertTrue(selection["fridge_binding_revision"])
        for adapted in (False, True):
            result, generator = self.generate([selection], adapted=adapted)
            self.assertEqual(result["status"], "success", result)
            evidence = result["data"]["nutrition_ingredient_evidence"]
            self.assertEqual(evidence[0]["source"], "product_label")
            self.assertEqual(evidence[0]["contribution"]["calories"], 240)
            self.assertEqual(result["data"]["computed_nutrition"]["calories"], 120)
            self.assertEqual(generator.call_args.args[0], ["หมูสับ", "holy basil leaves"])
        updated = self.update_item(row, name="minced pork").json()["data"]
        self.assertFalse(updated["barcode_product"]["active"])
        self.assertNotEqual(updated["barcode_product"]["revision"], selection["fridge_binding_revision"])
        rows = self.alice.get("/api/history").json()["data"]
        saved = next(row for row in rows if row["id"] == result["data"]["history_id"])
        self.assertEqual(saved["recipe_data"]["nutrition_ingredient_evidence"], evidence)
        regenerated, _ = self.generate([self.selection(updated)])
        fallback = regenerated["data"]["nutrition_ingredient_evidence"][0]
        self.assertEqual((fallback["source"], fallback["reason"]), ("INMU", "product_relink_required"))

    def test_catalog_and_legacy_items_cannot_promote_client_nutrition(self):
        row = self.create_item(barcode=None)
        result, _ = self.generate([self.selection(row)])
        evidence = result["data"]["nutrition_ingredient_evidence"][0]
        self.assertEqual((evidence["source"], evidence["reason"]), ("INMU", "product_legacy_basis"))
        self.assertEqual(result["data"]["computed_nutrition"]["calories"], 80)
        result, _ = self.generate([{"name": row["name"], "id": row["id"]}], adapted=True)
        self.assertEqual(result["data"]["computed_nutrition"]["calories"], 80)

    def test_foreign_missing_stale_and_duplicate_selections_stop_before_generation(self):
        row = self.create_item()
        selection = self.selection(row)
        bob = self.login("barcode-bob@example.com")
        for client, entry in ((bob, selection), (self.alice, {**selection, "fridge_ingredient_id": 9999}),
                              (self.alice, {**selection, "fridge_binding_revision": "stale"})):
            result, generator = self.generate([entry], client=client)
            self.assertEqual(result.get("code"), "fridge_selection_stale")
            generator.assert_not_called()
        result, generator = self.generate([selection, {"name": "minced pork"}])
        self.assertEqual(result.get("code"), "fridge_selection_conflict")
        generator.assert_not_called()
        with patch("main.load_barcode_binding") as provider:
            foreign = bob.put(f'/api/user-ingredients/{row["id"]}', headers=self.origin,
                              json={"barcode_code": BARCODE})
        self.assertEqual(foreign.status_code, 404)
        provider.assert_not_called()

    def test_two_rows_with_same_name_use_the_explicitly_selected_product(self):
        self.create_item()
        other = deepcopy(LABEL)
        other.update(barcode="8858998581023", product_name="Minced pork B")
        other["sets"][0]["macros"]["calories"] = 160
        row = self.create_item(barcode=other["barcode"], label=other)
        result, _ = self.generate([self.selection(row)])
        evidence = result["data"]["nutrition_ingredient_evidence"][0]
        self.assertEqual(evidence["barcode"], other["barcode"])
        self.assertEqual(result["data"]["computed_nutrition"]["calories"], 160)

    def test_unused_fridge_product_does_not_attach_to_another_declaration(self):
        milk = self.create_item(name="นมจืด", label={**LABEL, "product_name": "Milk A"})
        result, _ = self.generate([self.selection(milk), {"name": "minced pork"}])
        evidence = result["data"]["nutrition_ingredient_evidence"]
        self.assertEqual(evidence[0]["source"], "INMU")
        self.assertFalse(any(entry.get("barcode") == BARCODE for entry in evidence))

    def test_relink_preserves_item_and_failed_lookup_leaves_prior_binding(self):
        row = self.create_item()
        self.assertIn("barcode_product", row)
        resized = self.update_item(row).json()["data"]
        self.assertEqual(resized["barcode_product"], row["barcode_product"])
        from barcode_nutrition import BarcodeNutritionLookupError

        with patch("main.load_barcode_binding", side_effect=BarcodeNutritionLookupError("not found")):
            failed = self.update_item(row, barcode_code=BARCODE, name="will not be saved")
        self.assertEqual(failed.status_code, 502)
        self.assertEqual(self.alice.get("/api/user-ingredients").json()["data"], [resized])

        with patch("main.load_barcode_binding", return_value={**LABEL, "sets": []}):
            relinked = self.alice.put(f'/api/user-ingredients/{row["id"]}', headers=self.origin,
                                      json={"barcode_code": BARCODE}).json()["data"]
        self.assertEqual(relinked["id"], row["id"])
        self.assertEqual(relinked["quantity_amount"], resized["quantity_amount"])
        self.assertNotEqual(relinked["barcode_product"]["revision"], row["barcode_product"]["revision"])
        result, _ = self.generate([self.selection(relinked)])
        evidence = result["data"]["nutrition_ingredient_evidence"][0]
        self.assertEqual((evidence["source"], evidence["reason"]), ("INMU", "product_label_unavailable"))
