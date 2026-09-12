import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.db import get_db
from database.models import Base, PasswordResetOtp, RefreshToken, User
from main import app


class PasswordResetEndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[User.__table__, RefreshToken.__table__, PasswordResetOtp.__table__],
        )
        Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.Session = Session

        def override_get_db():
            db = Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.origin_headers = {"Origin": "http://127.0.0.1:5173"}

    def tearDown(self):
        app.dependency_overrides.clear()

    def _register(self, client, email, password="hunter22"):
        return client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
            headers=self.origin_headers,
        )

    def test_forgot_password_generic_response_for_unknown_email(self):
        client = TestClient(app)
        res = client.post(
            "/api/auth/forgot-password",
            json={"email": "nobody@example.com"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")

    def test_forgot_password_generic_response_for_known_email_and_creates_row(self):
        client = TestClient(app)
        self._register(client, "fp1@example.com")

        res = client.post(
            "/api/auth/forgot-password",
            json={"email": "fp1@example.com"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")

        db = self.Session()
        rows = db.query(PasswordResetOtp).all()
        self.assertEqual(len(rows), 1)

    def test_known_and_unknown_email_get_identical_response_body(self):
        client = TestClient(app)
        self._register(client, "fp2@example.com")

        known = client.post(
            "/api/auth/forgot-password",
            json={"email": "fp2@example.com"},
            headers=self.origin_headers,
        )
        unknown = client.post(
            "/api/auth/forgot-password",
            json={"email": "definitely-nobody@example.com"},
            headers=self.origin_headers,
        )
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.json(), unknown.json())

    def test_resend_within_cooldown_does_not_create_second_row(self):
        client = TestClient(app)
        self._register(client, "fp3@example.com")

        client.post(
            "/api/auth/forgot-password",
            json={"email": "fp3@example.com"},
            headers=self.origin_headers,
        )
        client.post(
            "/api/auth/forgot-password",
            json={"email": "fp3@example.com"},
            headers=self.origin_headers,
        )

        db = self.Session()
        rows = db.query(PasswordResetOtp).all()
        self.assertEqual(len(rows), 1)

    def test_resend_after_cooldown_invalidates_prior_and_creates_new_row(self):
        client = TestClient(app)
        self._register(client, "fp4@example.com")

        client.post(
            "/api/auth/forgot-password",
            json={"email": "fp4@example.com"},
            headers=self.origin_headers,
        )

        db = self.Session()
        first_row = db.query(PasswordResetOtp).one()
        # Simulate cooldown elapsed by backdating created_at directly.
        first_row.created_at = datetime.now(timezone.utc) - timedelta(seconds=61)
        db.commit()

        client.post(
            "/api/auth/forgot-password",
            json={"email": "fp4@example.com"},
            headers=self.origin_headers,
        )

        db2 = self.Session()
        rows = db2.query(PasswordResetOtp).all()
        self.assertEqual(len(rows), 2)
        refreshed_first = db2.get(PasswordResetOtp, first_row.id)
        now = datetime.now(timezone.utc)
        expires = refreshed_first.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        self.assertLessEqual(expires, now)

    def test_forgot_password_without_trusted_origin_is_403(self):
        client = TestClient(app)
        res = client.post("/api/auth/forgot-password", json={"email": "x@example.com"})
        self.assertEqual(res.status_code, 403)

    def test_delivery_failure_does_not_leave_a_row_behind(self):
        client = TestClient(app)
        self._register(client, "fp5@example.com")

        with mock.patch("main.send_otp_email", side_effect=RuntimeError("smtp down")):
            res = client.post(
                "/api/auth/forgot-password",
                json={"email": "fp5@example.com"},
                headers=self.origin_headers,
            )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")

        db = self.Session()
        rows = db.query(PasswordResetOtp).all()
        self.assertEqual(len(rows), 0)


if __name__ == "__main__":
    unittest.main()
