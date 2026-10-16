import unittest
from copy import deepcopy
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from database.db import get_db
from database.models import Base, BaseRecipe, IngredientNutrition, IngredientNutritionAlias, RecipeIngredientImage
from main import app, GenerateRecipeTextRequest
from generators.prompts import build_recipe_prompt
from nutrition.calculator import compute_quantities_nutrition
from test_nutrition_evidence import synthetic_match


class BaseNutritionEndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=[model.__table__ for model in (BaseRecipe, IngredientNutrition, IngredientNutritionAlias, RecipeIngredientImage)])
        self.db = Session(self.engine, autoflush=False)
        food = IngredientNutrition(ingredient_name="kale", unit_basis="100g", source="USDA", source_ref="test", calories=100, protein_g=10, carbs_g=20, fat_g=5)
        self.db.add(food)
        self.db.flush()
        self.db.add(IngredientNutritionAlias(alias="kale", ingredient_nutrition_id=food.id))
        self.recipe = BaseRecipe(name="Base menu", ingredients=["kale"], instructions=["Cook"], servings=2, ingredient_quantities=[{"name": "kale", "quantity_g": 200}], nutrition={"calories": 999, "protein_g": 999})
        self.db.add(self.recipe)
        self.db.commit()
        self.client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_calculates_fresh_per_serving_totals_without_writing_or_using_legacy_values(self):
        before = deepcopy(self.recipe.nutrition)
        with patch.object(self.db, "commit", side_effect=AssertionError("GET must not write")), patch.object(self.db, "flush", side_effect=AssertionError("GET must not flush")):
            response = self.client.get("/api/recipes")
        self.assertEqual(response.status_code, 200)
        row = response.json()["data"][0]
        self.assertEqual(row["nutrition"], {"basis": "per_serving", "calories": 100, "protein_g": 10, "carbs_g": 20, "fat_g": 5})
        self.assertEqual(row["computed_nutrition"], row["nutrition"])
        self.assertEqual(row["nutrition_origin"], "base_calculation")
        self.assertEqual(row["nutrition_calculation_status"], "limited")
        self.assertTrue(row["nutrition_partially_estimated"])
        self.assertEqual(row["nutrition_calculation_reasons"], ["source_unverified"])
        self.assertEqual(row["servings"], 2)
        self.assertNotIn("llm_estimated_nutrition", row)
        self.db.expire_all()
        self.assertEqual(self.db.get(BaseRecipe, self.recipe.id).nutrition, before)
        self.assertFalse(self.db.dirty)

    def test_time_range_and_missing_time_are_read_only_additive_fields(self):
        for minimum, maximum in ((None, None), (15, 20), (15, 15)):
            with self.subTest(minimum=minimum, maximum=maximum):
                self.recipe.total_time_min_minutes = minimum
                self.recipe.total_time_max_minutes = maximum
                self.db.commit()
                with patch.object(self.db, "commit", side_effect=AssertionError("GET must not write")), \
                        patch.object(self.db, "flush", side_effect=AssertionError("GET must not flush")):
                    row = self.client.get("/api/recipes").json()["data"][0]
                self.assertEqual(row["estimated_total_time"], None if minimum is None else
                                 {"min_minutes": minimum, "max_minutes": maximum})
                self.assertEqual(row["nutrition"]["calories"], 100)
                self.assertNotIn("usage_time", row)
                self.assertFalse(self.db.dirty)

    def test_time_constraint_rejects_partial_zero_negative_and_reversed_ranges(self):
        for minimum, maximum in ((None, 20), (15, None), (0, 20), (-1, 20), (20, 15)):
            with self.subTest(minimum=minimum, maximum=maximum):
                self.recipe.total_time_min_minutes = minimum
                self.recipe.total_time_max_minutes = maximum
                with self.assertRaises(IntegrityError):
                    self.db.commit()
                self.db.rollback()

    def test_changed_actual_amount_changes_response_without_changing_legacy_nutrition(self):
        self.recipe.ingredient_quantities = [{"name": "kale", "quantity_g": 100}]
        self.db.commit()
        row = self.client.get("/api/recipes").json()["data"][0]
        self.assertEqual(row["nutrition"]["calories"], 50)
        self.assertEqual(self.recipe.nutrition["calories"], 999)

    def test_bad_recipe_inputs_leave_values_absent_and_do_not_block_the_next_recipe(self):
        good = BaseRecipe(name="Good", ingredients=["kale"], instructions=[], servings=1, ingredient_quantities=[{"name": "kale", "quantity_g": 100}], nutrition={"calories": 888})
        self.db.add(good)
        self.db.commit()
        cases = [(None, 1), ([], 1), ([{"name": "kale", "quantity_g": 100}], None),
                 ([{"name": "kale", "quantity_g": 100}], 0), ([{"name": "missing", "quantity_g": 100}], 1),
                 ([{"name": "kale"}], 1), ([{"name": "kale", "quantity_g": -1}], 1),
                 ([{"name": "kale", "quantity_g": True}], 1), ([{"name": "", "quantity_g": 100}], 1),
                 ({"name": "kale", "quantity_g": 100}, 1), ([None], 1)]
        for quantities, servings in cases:
            with self.subTest(quantities=quantities, servings=servings):
                self.recipe.ingredient_quantities, self.recipe.servings = quantities, servings
                self.db.commit()
                rows = self.client.get("/api/recipes").json()["data"]
                self.assertEqual(len(rows), 2)
                self.assertIsNone(rows[0]["nutrition"])
                self.assertIsNone(rows[0]["computed_nutrition"])
                self.assertEqual(rows[0]["nutrition_calculation_status"], "unavailable")
                self.assertEqual(rows[1]["nutrition"]["calories"], 100)

    def test_missing_or_unsupported_macro_rows_never_become_zero_totals(self):
        food = self.db.scalar(select(IngredientNutrition))
        for field, value in (("protein_g", None), ("unit_basis", "100ml")):
            with self.subTest(field=field):
                old = getattr(food, field)
                setattr(food, field, value)
                self.db.commit()
                row = self.client.get("/api/recipes").json()["data"][0]
                self.assertIsNone(row["nutrition"])
                setattr(food, field, old)
                self.db.commit()

    def test_accepted_evidence_is_calculated_and_proxy_is_still_limited(self):
        match = synthetic_match(alias="kale", full_name="kale, raw")
        with patch("nutrition.calculator.match_ingredient", return_value=match):
            row = self.client.get("/api/recipes").json()["data"][0]
        self.assertEqual(row["nutrition_calculation_status"], "calculated")
        self.assertFalse(row["nutrition_partially_estimated"])
        self.assertEqual(row["nutrition_calculation_reasons"], [])
        match.derivation["proxy"] = "similar vegetable"
        with patch("nutrition.calculator.match_ingredient", return_value=match):
            row = self.client.get("/api/recipes").json()["data"][0]
        self.assertEqual(row["nutrition_calculation_status"], "limited")
        self.assertIn("proxy_composition", row["nutrition_calculation_reasons"])

    def test_constants_are_not_certified_as_grounded(self):
        result = compute_quantities_nutrition(self.db, [{"name": "เกลือ", "quantity_g": 1}], 1)
        self.assertTrue(result.partially_estimated)
        self.assertIn("constant_unverified", result.partially_estimated_reasons)

    def test_response_with_and_without_calculation_remains_a_valid_generation_input(self):
        for quantities in ([{"name": "kale", "quantity_g": 100}], []):
            with self.subTest(quantities=quantities):
                self.recipe.ingredient_quantities = quantities
                self.db.commit()
                row = self.client.get("/api/recipes").json()["data"][0]
                request = GenerateRecipeTextRequest(recipe=row, ingredients=[{"name": "kale"}], preferences={})
                prompt = build_recipe_prompt(request.ingredients, request.preferences, request.recipe)
                self.assertIn("Base menu", prompt)
                self.assertNotIn("999", prompt)

