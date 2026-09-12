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

    @mock.patch("otp.generate_otp_code", return_value="424242")
    def test_verify_otp_succeeds_with_correct_code_and_returns_ticket(self, _mock):
        client = TestClient(app)
        self._register(client, "vo1@example.com")
        client.post(
            "/api/auth/forgot-password",
            json={"email": "vo1@example.com"},
            headers=self.origin_headers,
        )

        res = client.post(
            "/api/auth/verify-otp",
            json={"email": "vo1@example.com", "code": "424242"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["data"]["reset_ticket"])

    @mock.patch("otp.generate_otp_code", return_value="424242")
    def test_verify_otp_fails_with_wrong_code(self, _mock):
        client = TestClient(app)
        self._register(client, "vo2@example.com")
        client.post(
            "/api/auth/forgot-password",
            json={"email": "vo2@example.com"},
            headers=self.origin_headers,
        )

        res = client.post(
            "/api/auth/verify-otp",
            json={"email": "vo2@example.com", "code": "000000"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["status"], "error")

    def test_verify_otp_fails_for_unknown_email(self):
        client = TestClient(app)
        res = client.post(
            "/api/auth/verify-otp",
            json={"email": "nobody@example.com", "code": "123456"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 400)

    @mock.patch("otp.generate_otp_code", return_value="424242")
    def test_verify_otp_cannot_be_reused_after_success(self, _mock):
        client = TestClient(app)
        self._register(client, "vo3@example.com")
        client.post(
            "/api/auth/forgot-password",
            json={"email": "vo3@example.com"},
            headers=self.origin_headers,
        )

        first = client.post(
            "/api/auth/verify-otp",
            json={"email": "vo3@example.com", "code": "424242"},
            headers=self.origin_headers,
        )
        self.assertEqual(first.status_code, 200)

        second = client.post(
            "/api/auth/verify-otp",
            json={"email": "vo3@example.com", "code": "424242"},
            headers=self.origin_headers,
        )
        self.assertEqual(second.status_code, 400)

    @mock.patch("otp.generate_otp_code", return_value="424242")
    def test_fifth_wrong_attempt_locks_out_even_the_correct_code(self, _mock):
        client = TestClient(app)
        self._register(client, "vo4@example.com")
        client.post(
            "/api/auth/forgot-password",
            json={"email": "vo4@example.com"},
            headers=self.origin_headers,
        )

        for _ in range(5):
            client.post(
                "/api/auth/verify-otp",
                json={"email": "vo4@example.com", "code": "000000"},
                headers=self.origin_headers,
            )

        res = client.post(
            "/api/auth/verify-otp",
            json={"email": "vo4@example.com", "code": "424242"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 400)

    def test_verify_otp_without_trusted_origin_is_403(self):
        client = TestClient(app)
        res = client.post("/api/auth/verify-otp", json={"email": "x@example.com", "code": "123456"})
        self.assertEqual(res.status_code, 403)

    @mock.patch("otp.generate_otp_code", return_value="424242")
    def test_reset_password_succeeds_and_new_password_works(self, _mock):
        client = TestClient(app)
        self._register(client, "rp1@example.com")
        client.post("/api/auth/forgot-password", json={"email": "rp1@example.com"}, headers=self.origin_headers)
        verify_res = client.post(
            "/api/auth/verify-otp",
            json={"email": "rp1@example.com", "code": "424242"},
            headers=self.origin_headers,
        )
        ticket = verify_res.json()["data"]["reset_ticket"]

        res = client.post(
            "/api/auth/reset-password",
            json={"reset_ticket": ticket, "new_password": "newpassword123"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 200)

        login_res = client.post(
            "/api/auth/login",
            data={"username": "rp1@example.com", "password": "newpassword123"},
            headers=self.origin_headers,
        )
        self.assertEqual(login_res.status_code, 200)

    def test_reset_password_fails_with_invalid_ticket(self):
        client = TestClient(app)
        res = client.post(
            "/api/auth/reset-password",
            json={"reset_ticket": "not-a-real-ticket", "new_password": "newpassword123"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 400)

    @mock.patch("otp.generate_otp_code", return_value="424242")
    def test_reset_password_ticket_is_single_use(self, _mock):
        client = TestClient(app)
        self._register(client, "rp2@example.com")
        client.post("/api/auth/forgot-password", json={"email": "rp2@example.com"}, headers=self.origin_headers)
        verify_res = client.post(
            "/api/auth/verify-otp",
            json={"email": "rp2@example.com", "code": "424242"},
            headers=self.origin_headers,
        )
        ticket = verify_res.json()["data"]["reset_ticket"]

        first = client.post(
            "/api/auth/reset-password",
            json={"reset_ticket": ticket, "new_password": "newpassword123"},
            headers=self.origin_headers,
        )
        self.assertEqual(first.status_code, 200)

        second = client.post(
            "/api/auth/reset-password",
            json={"reset_ticket": ticket, "new_password": "anotherpassword456"},
            headers=self.origin_headers,
        )
        self.assertEqual(second.status_code, 400)

    @mock.patch("otp.generate_otp_code", return_value="424242")
    def test_reset_password_enforces_length_policy(self, _mock):
        client = TestClient(app)
        self._register(client, "rp3@example.com")
        client.post("/api/auth/forgot-password", json={"email": "rp3@example.com"}, headers=self.origin_headers)
        verify_res = client.post(
            "/api/auth/verify-otp",
            json={"email": "rp3@example.com", "code": "424242"},
            headers=self.origin_headers,
        )
        ticket = verify_res.json()["data"]["reset_ticket"]

        res = client.post(
            "/api/auth/reset-password",
            json={"reset_ticket": ticket, "new_password": "short"},
            headers=self.origin_headers,
        )
        self.assertEqual(res.status_code, 400)

    @mock.patch("otp.generate_otp_code", return_value="424242")
    def test_reset_password_revokes_all_refresh_tokens(self, _mock):
        client = TestClient(app)
        self._register(client, "rp4@example.com")
        login_res = client.post(
            "/api/auth/login",
            data={"username": "rp4@example.com", "password": "hunter22"},
            headers=self.origin_headers,
        )
        self.assertEqual(login_res.status_code, 200)

        client.post("/api/auth/forgot-password", json={"email": "rp4@example.com"}, headers=self.origin_headers)
        verify_res = client.post(
            "/api/auth/verify-otp",
            json={"email": "rp4@example.com", "code": "424242"},
            headers=self.origin_headers,
        )
        ticket = verify_res.json()["data"]["reset_ticket"]

        client.post(
            "/api/auth/reset-password",
            json={"reset_ticket": ticket, "new_password": "newpassword123"},
            headers=self.origin_headers,
        )

        db = self.Session()
        user_id = db.query(User).filter_by(email="rp4@example.com").one().id
        tokens = db.query(RefreshToken).filter_by(user_id=user_id).all()
        self.assertTrue(tokens)
        self.assertTrue(all(t.revoked_at is not None for t in tokens))

    def test_reset_password_without_trusted_origin_is_403(self):
        client = TestClient(app)
        res = client.post(
            "/api/auth/reset-password",
            json={"reset_ticket": "x", "new_password": "newpassword123"},
        )
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
