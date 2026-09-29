import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from base_favorites_repository import set_base_favorite
from database.db import get_db
from database.models import (
    Base,
    BaseRecipe,
    BaseRecipeFavorite,
    RefreshToken,
    User,
)
from main import app


class BaseFavoritesTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[
                User.__table__,
                RefreshToken.__table__,
                BaseRecipe.__table__,
                BaseRecipeFavorite.__table__,
            ],
        )
        self.session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = self.session_local()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.origin = {"Origin": "http://127.0.0.1:5173"}
        with self.session_local() as db:
            for recipe_id in (1, 2, 3):
                db.add(
                    BaseRecipe(
                        id=recipe_id,
                        name=f"Recipe {recipe_id}",
                        tags=[],
                        ingredients=[],
                        nutrition={},
                        instructions=[],
                    )
                )
            db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()

    def login(self, email, password="hunter22"):
        client = TestClient(app)
        client.post("/api/auth/register", json={"email": email, "password": password}, headers=self.origin)
        client.post("/api/auth/login", data={"username": email, "password": password}, headers=self.origin)
        return client

    def user_id(self, email):
        with self.session_local() as db:
            return db.execute(select(User.id).where(User.email == email)).scalar_one()

    def put(self, client, recipe_id, headers=None):
        return client.put(
            f"/api/base-favorites/{recipe_id}", headers=self.origin if headers is None else headers
        )

    def delete(self, client, recipe_id, headers=None):
        return client.delete(
            f"/api/base-favorites/{recipe_id}", headers=self.origin if headers is None else headers
        )

    def ids(self, client):
        res = client.get("/api/base-favorites")
        self.assertEqual(res.status_code, 200)
        return res.json()["data"]


class BaseFavoritesEndpointTests(BaseFavoritesTestCase):
    def setUp(self):
        super().setUp()
        self.alice = self.login("alice@example.com")

    def test_empty_list(self):
        res = self.alice.get("/api/base-favorites")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "success", "data": []})

    def test_put_adds_in_creation_order(self):
        res = self.put(self.alice, 1)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "success", "data": {"is_favorite": True}})
        self.assertEqual(self.ids(self.alice), [1])
        self.assertEqual(self.put(self.alice, 2).status_code, 200)
        self.assertEqual(self.ids(self.alice), [1, 2])

    def test_creation_order_not_recipe_id_order(self):
        self.put(self.alice, 3)
        self.put(self.alice, 1)
        self.assertEqual(self.ids(self.alice), [3, 1])

    def test_put_twice_is_idempotent(self):
        self.assertEqual(self.put(self.alice, 1).status_code, 200)
        self.assertEqual(self.put(self.alice, 1).status_code, 200)
        self.assertEqual(self.ids(self.alice), [1])

    def test_delete_removes_and_is_idempotent(self):
        self.put(self.alice, 1)
        res = self.delete(self.alice, 1)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "success", "data": {"is_favorite": False}})
        self.assertEqual(self.delete(self.alice, 1).status_code, 200)
        self.assertEqual(self.ids(self.alice), [])

    def test_unknown_recipe_put_404_delete_200(self):
        res = self.put(self.alice, 999)
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["detail"], "Recipe not found")
        res = self.delete(self.alice, 999)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "success", "data": {"is_favorite": False}})
        self.assertEqual(self.ids(self.alice), [])

    def test_users_are_isolated(self):
        bob = self.login("bob@example.com")
        self.put(self.alice, 1)
        self.assertEqual(self.ids(bob), [])
        self.assertEqual(self.delete(bob, 1).status_code, 200)
        self.assertEqual(self.ids(self.alice), [1])
        self.assertEqual(self.put(bob, 1).status_code, 200)
        self.assertEqual(self.ids(bob), [1])
        self.assertEqual(self.ids(self.alice), [1])

    def test_requires_login(self):
        anon = TestClient(app)
        self.assertEqual(anon.get("/api/base-favorites").status_code, 401)
        self.assertEqual(self.put(anon, 1).status_code, 401)
        self.assertEqual(self.delete(anon, 1).status_code, 401)

    def test_writes_require_trusted_origin(self):
        self.assertEqual(self.put(self.alice, 1, headers={}).status_code, 403)
        self.assertEqual(self.delete(self.alice, 1, headers={}).status_code, 403)
        self.assertEqual(self.ids(self.alice), [])

    def test_id_bounds(self):
        for bad in (2147483648, 0):
            self.assertEqual(self.put(self.alice, bad).status_code, 422, bad)
            self.assertEqual(self.delete(self.alice, bad).status_code, 422, bad)
        self.assertEqual(self.put(self.alice, 2147483647).status_code, 404)
        self.assertEqual(self.delete(self.alice, 2147483647).status_code, 200)


class BaseFavoritesRepositoryTests(BaseFavoritesTestCase):
    def test_set_favorite_missing_recipe_returns_false_and_writes_nothing(self):
        self.login("alice@example.com")
        user_id = self.user_id("alice@example.com")
        with self.session_local() as db:
            self.assertFalse(set_base_favorite(db, user_id=user_id, base_recipe_id=999, favorite=True))
        with self.session_local() as db:
            self.assertEqual(db.execute(select(BaseRecipeFavorite)).scalars().all(), [])


if __name__ == "__main__":
    unittest.main()
