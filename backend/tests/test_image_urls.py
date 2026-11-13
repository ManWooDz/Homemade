import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import get_db
from database.models import Base, BaseRecipe, RecipeIngredientImage
from main import app


class RecipesEndpointImageRegressionTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine, tables=[BaseRecipe.__table__, RecipeIngredientImage.__table__])
        session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        db = session_local()
        db.add_all([
            BaseRecipe(id=1, name="local", image="images/pad.png", tags=[], ingredients=[], nutrition={}, instructions=[]),
            BaseRecipe(id=2, name="remote", image="https://cdn.example.com/a.png", tags=[], ingredients=[], nutrition={}, instructions=[]),
            BaseRecipe(id=3, name="none", image=None, tags=[], ingredients=[], nutrition={}, instructions=[]),
        ])
        db.commit()
        db.close()

        def override_get_db():
            session = session_local()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_recipes_image_urls_unchanged(self):
        data = TestClient(app).get("/api/recipes").json()["data"]
        images = {row["name"]: row["image"] for row in data}
        self.assertEqual(images["local"], "/images/pad.png")
        self.assertEqual(images["remote"], "https://cdn.example.com/a.png")
        self.assertIsNone(images["none"])


class PublicImageUrlTests(unittest.TestCase):
    def test_prefixes_relative_paths(self):
        from image_urls import public_image_url
        self.assertEqual(public_image_url("images/pad.png"), "/images/pad.png")

    def test_local_urls_use_the_current_origin(self):
        from image_urls import public_image_url
        for path in ("/images/pad.png", "http://localhost:8000/images/pad.png", "http://127.0.0.1:8000/images/pad.png"):
            with self.subTest(path=path):
                self.assertEqual(public_image_url(path), "/images/pad.png")

    def test_keeps_absolute_and_empty_values(self):
        from image_urls import public_image_url
        self.assertEqual(public_image_url("https://cdn.example.com/a.png"), "https://cdn.example.com/a.png")
        self.assertEqual(public_image_url("http://x/y.png"), "http://x/y.png")
        self.assertIsNone(public_image_url(None))
        self.assertEqual(public_image_url(""), "")

    def test_preserves_other_image_sources(self):
        from image_urls import public_image_url
        for path in ("http://localhost:8000.example.com/x.png", "//cdn.example.com/x.png", "data:image/png;base64,AAAA", "blob:https://example.com/image"):
            with self.subTest(path=path):
                self.assertEqual(public_image_url(path), path)

    def test_fridge_serialization_normalizes_legacy_image_without_changing_row(self):
        from fridge_repository import _public_ingredient
        original = "http://localhost:8000/images/ingredients/old.png"
        row = SimpleNamespace(id=1, name="demo", category="Other", image=original,
                              expiry_date=None, nutrition_data=None, quantity_amount=None, quantity_unit=None)
        self.assertEqual(_public_ingredient(row)["image"], "/images/ingredients/old.png")
        self.assertEqual(row.image, original)


if __name__ == "__main__":
    unittest.main()
