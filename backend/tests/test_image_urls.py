import os
import sys
import unittest

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
        self.assertEqual(images["local"], "http://localhost:8000/images/pad.png")
        self.assertEqual(images["remote"], "https://cdn.example.com/a.png")
        self.assertIsNone(images["none"])


class PublicImageUrlTests(unittest.TestCase):
    def test_prefixes_relative_paths(self):
        from image_urls import public_image_url
        self.assertEqual(public_image_url("images/pad.png"), "http://localhost:8000/images/pad.png")

    def test_keeps_absolute_and_empty_values(self):
        from image_urls import public_image_url
        self.assertEqual(public_image_url("https://cdn.example.com/a.png"), "https://cdn.example.com/a.png")
        self.assertEqual(public_image_url("http://x/y.png"), "http://x/y.png")
        self.assertIsNone(public_image_url(None))
        self.assertEqual(public_image_url(""), "")


if __name__ == "__main__":
    unittest.main()
