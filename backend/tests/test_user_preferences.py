import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import get_db
from database.models import Base, RefreshToken, User, UserPreference
from main import app


class UserPreferenceModelTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[User.__table__, UserPreference.__table__])
        self.db = Session(self.engine)
        user = User(email="prefs@example.com")
        self.db.add(user)
        self.db.commit()
        self.user_id = user.id

    def tearDown(self):
        self.db.close()

    def test_insert_and_query_round_trip(self):
        row = UserPreference(
            user_id=self.user_id,
            age=25,
            cuisine_preferences=["อาหารไทย"],
            dietary_restrictions=["แพ้ถั่ว"],
            equipment=["กระทะ"],
            cooking_frequency="ทำเป็นประจำ — 5–6 ครั้ง/สัปดาห์",
            cooking_goals=["ประหยัดค่าอาหาร"],
        )
        self.db.add(row)
        self.db.commit()

        fetched = self.db.get(UserPreference, self.user_id)
        self.assertEqual(fetched.age, 25)
        self.assertEqual(fetched.cuisine_preferences, ["อาหารไทย"])
        self.assertEqual(fetched.dietary_restrictions, ["แพ้ถั่ว"])

    def test_user_id_is_the_primary_key(self):
        row = UserPreference(user_id=self.user_id)
        self.db.add(row)
        self.db.commit()
        # PK lookup by user_id must work directly — no separate surrogate id
        self.assertIsNotNone(self.db.get(UserPreference, self.user_id))


class UserPreferenceEndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[User.__table__, RefreshToken.__table__, UserPreference.__table__],
        )
        test_session_local = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = test_session_local()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.origin_headers = {"Origin": "http://127.0.0.1:5173"}

    def tearDown(self):
        app.dependency_overrides.clear()

    def _register_and_login(self, email="prefs@example.com", password="hunter22"):
        self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
            headers=self.origin_headers,
        )
        return self.client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
            headers=self.origin_headers,
        )

    def _empty_body(self):
        return {
            "cuisine_preferences": [],
            "dietary_restrictions": [],
            "equipment": [],
            "cooking_goals": [],
        }

    def test_get_before_any_put_returns_null(self):
        self._register_and_login()
        res = self.client.get("/api/user-preferences")
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.json()["data"])

    def test_get_without_login_is_401(self):
        res = self.client.get("/api/user-preferences")
        self.assertEqual(res.status_code, 401)

    def test_put_then_get_round_trips(self):
        self._register_and_login()
        body = {
            "age": 25,
            "cuisine_preferences": ["อาหารไทย"],
            "dietary_restrictions": ["แพ้ถั่ว"],
            "equipment": ["กระทะ"],
            "cooking_frequency": "ทำเป็นประจำ — 5–6 ครั้ง/สัปดาห์",
            "cooking_goals": ["ประหยัดค่าอาหาร"],
        }
        put_res = self.client.put("/api/user-preferences", json=body, headers=self.origin_headers)
        self.assertEqual(put_res.status_code, 200)
        self.assertEqual(put_res.json()["data"]["age"], 25)

        get_res = self.client.get("/api/user-preferences")
        self.assertEqual(get_res.json()["data"]["cuisine_preferences"], ["อาหารไทย"])

    def test_put_upserts_not_duplicates(self):
        self._register_and_login()
        body = {"age": 20, **self._empty_body(), "cooking_frequency": None}
        self.client.put("/api/user-preferences", json=body, headers=self.origin_headers)
        body["age"] = 30
        self.client.put("/api/user-preferences", json=body, headers=self.origin_headers)
        get_res = self.client.get("/api/user-preferences")
        self.assertEqual(get_res.json()["data"]["age"], 30)

    def test_put_without_login_is_401(self):
        res = self.client.put(
            "/api/user-preferences", json=self._empty_body(), headers=self.origin_headers
        )
        self.assertEqual(res.status_code, 401)

    def test_put_without_trusted_origin_is_403(self):
        self._register_and_login()
        res = self.client.put("/api/user-preferences", json=self._empty_body())
        self.assertEqual(res.status_code, 403)

    def test_put_rejects_age_out_of_range(self):
        self._register_and_login()
        res = self.client.put(
            "/api/user-preferences",
            json={"age": 200, **self._empty_body()},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
