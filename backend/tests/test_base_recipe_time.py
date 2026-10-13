"""Base-menu time regressions independent of pending nutrition changes."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database.db import get_db
from database.models import Base, BaseRecipe, RecipeIngredientImage
from main import app


class BaseRecipeTimeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=[BaseRecipe.__table__, RecipeIngredientImage.__table__])
        self.db = Session(self.engine, autoflush=False)
        self.recipe = BaseRecipe(name="Time menu", ingredients=[], instructions=[], nutrition={})
        self.db.add(self.recipe)
        self.db.commit()
        self.client = TestClient(app)
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_time_range_and_missing_time_are_read_only_additive_fields(self):
        for minimum, maximum in ((None, None), (15, 20), (15, 15)):
            with self.subTest(minimum=minimum, maximum=maximum):
                self.recipe.total_time_min_minutes = minimum
                self.recipe.total_time_max_minutes = maximum
                self.db.commit()
                with patch.object(self.db, "commit", side_effect=AssertionError("GET must not write")), \
                        patch.object(self.db, "flush", side_effect=AssertionError("GET must not flush")):
                    response = self.client.get("/api/recipes")
                self.assertEqual(response.status_code, 200)
                row = response.json()["data"][0]
                self.assertEqual(row["estimated_total_time"], None if minimum is None else
                                 {"min_minutes": minimum, "max_minutes": maximum})
                self.assertEqual(row["name"], "Time menu")
                self.assertNotIn("usage_time", row)
                self.assertEqual(self.recipe.nutrition, {})
                self.assertFalse(self.db.dirty)

    def test_time_constraint_rejects_partial_zero_negative_and_reversed_ranges(self):
        for minimum, maximum in ((None, 20), (15, None), (0, 20), (-1, 20), (20, 15)):
            with self.subTest(minimum=minimum, maximum=maximum):
                self.recipe.total_time_min_minutes = minimum
                self.recipe.total_time_max_minutes = maximum
                with self.assertRaises(IntegrityError):
                    self.db.commit()
                self.db.rollback()
