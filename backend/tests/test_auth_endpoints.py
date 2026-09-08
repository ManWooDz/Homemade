import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import get_db
from database.models import Base, RefreshToken, User
from main import app


class AuthEndpointTests(unittest.TestCase):
    def setUp(self):
        # StaticPool + check_same_thread=False: FastAPI runs the sync
        # get_db dependency via run_in_threadpool, so each request can land
        # on a different OS thread. sqlite:///:memory:'s default pool
        # (SingletonThreadPool) hands each thread its own fresh, empty
        # in-memory database — StaticPool shares the single connection
        # across threads instead, which is required for this override to
        # see the tables created below.
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine, tables=[User.__table__, RefreshToken.__table__])
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

    def _register_and_login(self, email="user@example.com", password="hunter22"):
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

    def test_register_then_login_sets_both_cookies(self):
        res = self._register_and_login()
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(res.cookies.get("access_token"))
        self.assertIsNotNone(res.cookies.get("refresh_token"))

    def test_me_succeeds_after_login(self):
        self._register_and_login()
        res = self.client.get("/api/auth/me")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["email"], "user@example.com")

    def test_me_is_401_without_login(self):
        res = self.client.get("/api/auth/me")
        self.assertEqual(res.status_code, 401)

    def test_login_wrong_password_is_401(self):
        self.client.post(
            "/api/auth/register",
            json={"email": "user2@example.com", "password": "hunter22"},
            headers=self.origin_headers,
        )
        res = self.client.post(
            "/api/auth/login",
            data={"username": "user2@example.com", "password": "wrong"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 401)

    def test_refresh_rotates_cookies_and_me_still_works(self):
        self._register_and_login()
        old_refresh_cookie = self.client.cookies.get("refresh_token")
        res = self.client.post("/api/auth/refresh", headers=self.origin_headers)
        self.assertEqual(res.status_code, 200)
        new_refresh_cookie = self.client.cookies.get("refresh_token")
        self.assertNotEqual(old_refresh_cookie, new_refresh_cookie)
        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)

    def test_replaying_pre_rotation_refresh_cookie_is_rejected(self):
        self._register_and_login()
        captured_refresh = self.client.cookies.get("refresh_token")
        self.client.post("/api/auth/refresh", headers=self.origin_headers)  # rotates once
        # Simulate a second tab/request still holding the pre-rotation cookie
        self.client.cookies.set("refresh_token", captured_refresh)
        res = self.client.post("/api/auth/refresh", headers=self.origin_headers)
        self.assertEqual(res.status_code, 401)

    def test_refresh_with_invalid_cookie_clears_both_cookies_on_401(self):
        # Regression test for I-1: FastAPI only merges the injected Response
        # parameter's headers into the final response when the route handler
        # returns normally. Raising HTTPException makes Starlette build a
        # fresh response, silently discarding any Set-Cookie already set on
        # that Response object (e.g. by clear_auth_cookies) — so the old code
        # called clear_auth_cookies(response) then raised HTTPException, which
        # never actually cleared the cookies. This test asserts the 401
        # response itself carries Set-Cookie headers that clear both cookies,
        # not merely that the status code is 401.
        self.client.cookies.set("refresh_token", "not-a-real-token")
        res = self.client.post("/api/auth/refresh", headers=self.origin_headers)
        self.assertEqual(res.status_code, 401)

        set_cookie_headers = res.headers.get_list("set-cookie")
        access_clear = next(
            (h for h in set_cookie_headers if h.startswith("access_token=")), None
        )
        refresh_clear = next(
            (h for h in set_cookie_headers if h.startswith("refresh_token=")), None
        )
        self.assertIsNotNone(access_clear, f"no Set-Cookie cleared access_token; got {set_cookie_headers}")
        self.assertIsNotNone(refresh_clear, f"no Set-Cookie cleared refresh_token; got {set_cookie_headers}")
        self.assertIn("Path=/api", access_clear)
        self.assertIn("Path=/api/auth", refresh_clear)
        # A cleared cookie is expired (Max-Age=0 and/or an epoch Expires date)
        self.assertTrue("Max-Age=0" in access_clear or "expires=Thu, 01 Jan 1970" in access_clear)
        self.assertTrue("Max-Age=0" in refresh_clear or "expires=Thu, 01 Jan 1970" in refresh_clear)

    def test_logout_revokes_and_me_becomes_401(self):
        self._register_and_login()
        res = self.client.post("/api/auth/logout", headers=self.origin_headers)
        self.assertEqual(res.status_code, 200)
        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 401)

    def test_logout_with_no_prior_login_still_returns_200(self):
        res = self.client.post("/api/auth/logout", headers=self.origin_headers)
        self.assertEqual(res.status_code, 200)

    def test_mutation_without_trusted_origin_is_403(self):
        res = self.client.post(
            "/api/auth/login",
            data={"username": "nobody@example.com", "password": "whatever"},
        )
        self.assertEqual(res.status_code, 403)

    def test_access_cookie_has_expected_attributes(self):
        res = self._register_and_login()
        access_cookie_header = next(
            h for h in res.headers.get_list("set-cookie") if h.startswith("access_token=")
        )
        self.assertIn("HttpOnly", access_cookie_header)
        self.assertIn("Path=/api", access_cookie_header)
        self.assertIn("samesite=lax", access_cookie_header.lower())

    def test_refresh_cookie_path_is_scoped_to_api_auth(self):
        res = self._register_and_login()
        refresh_cookie_header = next(
            h for h in res.headers.get_list("set-cookie") if h.startswith("refresh_token=")
        )
        self.assertIn("Path=/api/auth", refresh_cookie_header)

    def test_access_cookie_not_sent_outside_api_path(self):
        # Path=/api means the browser (and httpx's RFC-6265-compliant
        # cookie jar) must not attach access_token to a request whose
        # path doesn't start with /api.
        self._register_and_login()
        res = self.client.get("/images/does-not-exist.png")
        self.assertNotIn("access_token", res.request.headers.get("cookie", ""))


if __name__ == "__main__":
    unittest.main()
