import importlib.util
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth import hash_password, verify_password
from database.db import get_db
from database.models import Base, PendingRegistration, PasswordResetOtp, RefreshToken, User
from main import app
import registration


class RegistrationEndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=[PendingRegistration.__table__, User.__table__, RefreshToken.__table__, PasswordResetOtp.__table__])
        self.Session = sessionmaker(bind=self.engine, autoflush=False)
        def override_db():
            with self.Session() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.headers = {"Origin": "http://127.0.0.1:5173"}
        self.sender_patch = patch("main.send_otp_email")
        self.sender = self.sender_patch.start()
        self.code_patch = patch("registration.generate_otp_code", return_value="123456")
        self.code_patch.start()

    def tearDown(self):
        self.sender_patch.stop()
        self.code_patch.stop()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def post(self, path, body):
        return self.client.post("/api/auth/" + path, json=body, headers=self.headers)

    def start(self, email="new@example.com", password="passwordA1"):
        res = self.post("register", {"email": email, "password": password})
        self.assertEqual(res.status_code, 202, res.text)
        return res.json()["data"]["registration_token"]

    def verify(self, token, code="123456"):
        return self.post("verify-registration", {"registration_token": token, "code": code})

    def age(self, **values):
        with self.Session() as db:
            row = db.query(PendingRegistration).one()
            for key, value in values.items():
                setattr(row, key, value)
            db.commit()

    def test_account_and_session_exist_only_after_verification(self):
        token = self.start("  NEW@example.com ")
        self.sender.assert_called_once_with("new@example.com", "123456", purpose="registration")
        with self.Session() as db:
            self.assertEqual(db.query(User).count(), 0)
            self.assertEqual(db.query(RefreshToken).count(), 0)
            row = db.query(PendingRegistration).one()
            self.assertNotEqual(row.registration_token_hash, token)
            self.assertNotEqual(row.code_hash, "123456")
            self.assertNotEqual(row.hashed_password, "passwordA1")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", data={"username": "new@example.com", "password": "passwordA1"}, headers=self.headers).status_code, 401)
        res = self.verify(token)
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.headers["Cache-Control"], "no-store")
        self.assertTrue(res.cookies.get("access_token"))
        self.assertTrue(res.cookies.get("refresh_token"))
        self.assertEqual(self.client.get("/api/auth/me").json()["data"]["email"], "new@example.com")
        with self.Session() as db:
            row = db.query(PendingRegistration).one()
            self.assertIsNotNone(row.consumed_at)
            self.assertIsNone(row.hashed_password)
            self.assertIsNone(row.code_hash)
            self.assertTrue(verify_password("passwordA1", db.query(User).one().hashed_password))
        self.assertEqual(self.verify(token).status_code, 400)

    def test_wrong_codes_persist_cap_and_resend_cannot_reset_it(self):
        token = self.start()
        for _ in range(5):
            self.assertEqual(self.verify(token, "000000").status_code, 400)
        self.assertEqual(self.verify(token).status_code, 400)
        self.age(last_sent_at=datetime.now(timezone.utc) - timedelta(minutes=2))
        self.assertEqual(self.post("resend-registration", {"registration_token": token}).status_code, 429)
        self.assertEqual(self.post("register", {"email": "new@example.com", "password": "replacement1"}).status_code, 429)
        with self.Session() as db:
            self.assertEqual(db.query(PendingRegistration).one().attempts, 5)
            self.assertEqual(db.query(User).count(), 0)

    def test_expired_code_can_be_resent_but_old_code_is_invalid(self):
        token = self.start()
        now = datetime.now(timezone.utc)
        self.age(expires_at=now - timedelta(seconds=1), last_sent_at=now - timedelta(minutes=11))
        self.assertEqual(self.verify(token).status_code, 400)
        with patch("registration.generate_otp_code", return_value="654321"):
            self.assertEqual(self.post("resend-registration", {"registration_token": token}).status_code, 200)
        self.assertEqual(self.verify(token).status_code, 400)
        self.assertEqual(self.verify(token, "654321").status_code, 200)

    def test_resend_keeps_prior_guesses_and_limits_by_email(self):
        token = self.start()
        self.verify(token, "000000")
        self.assertEqual(self.post("resend-registration", {"registration_token": token}).status_code, 429)
        self.assertEqual(self.post("register", {"email": "NEW@example.com", "password": "passwordB1"}).status_code, 429)
        for _ in range(4):
            self.age(last_sent_at=datetime.now(timezone.utc) - timedelta(minutes=2))
            self.assertEqual(self.post("resend-registration", {"registration_token": token}).status_code, 200)
        self.age(last_sent_at=datetime.now(timezone.utc) - timedelta(minutes=2))
        self.assertEqual(self.post("resend-registration", {"registration_token": token}).status_code, 429)
        with self.Session() as db:
            row = db.query(PendingRegistration).one()
            self.assertEqual((row.attempts, row.send_count), (1, 5))

    def test_new_registration_rotates_token_and_binds_new_password(self):
        old_token = self.start()
        self.age(last_sent_at=datetime.now(timezone.utc) - timedelta(minutes=2))
        token = self.start(password="passwordB1")
        self.assertNotEqual(token, old_token)
        self.assertEqual(self.verify(old_token).status_code, 400)
        self.assertEqual(self.verify(token).status_code, 200)
        with self.Session() as db:
            user = db.query(User).one()
            self.assertTrue(verify_password("passwordB1", user.hashed_password))
            self.assertFalse(verify_password("passwordA1", user.hashed_password))

    def test_delivery_failure_rolls_back_initial_registration(self):
        self.sender.side_effect = RuntimeError("smtp secret failure")
        res = self.post("register", {"email": "new@example.com", "password": "passwordA1"})
        self.assertEqual(res.status_code, 503)
        self.assertNotIn("secret", res.text)
        with self.Session() as db:
            self.assertEqual(db.query(PendingRegistration).count(), 0)
            self.assertEqual(db.query(User).count(), 0)

    def test_failed_resend_or_restart_preserves_prior_code_and_credentials(self):
        token = self.start()
        self.age(last_sent_at=datetime.now(timezone.utc) - timedelta(minutes=2))
        self.sender.side_effect = RuntimeError("SMTP down")
        self.assertEqual(self.post("resend-registration", {"registration_token": token}).status_code, 503)
        self.assertEqual(self.post("register", {"email": "new@example.com", "password": "passwordB1"}).status_code, 503)
        self.assertEqual(self.verify(token).status_code, 200)
        with self.Session() as db:
            self.assertTrue(verify_password("passwordA1", db.query(User).one().hashed_password))

    def test_activation_commit_failure_does_not_burn_code_or_issue_session(self):
        token = self.start()
        with patch("sqlalchemy.orm.Session.commit", side_effect=RuntimeError("commit failed")):
            res = self.verify(token)
        self.assertEqual(res.status_code, 503)
        self.assertFalse(res.cookies.get("access_token"))
        with self.Session() as db:
            self.assertEqual(db.query(User).count(), 0)
            self.assertEqual(db.query(RefreshToken).count(), 0)
            self.assertIsNone(db.query(PendingRegistration).one().consumed_at)
        self.assertEqual(self.verify(token).status_code, 200)

    def test_legacy_account_works_and_cannot_be_overwritten(self):
        with self.Session() as db:
            db.add(User(email="legacy@example.com", hashed_password=hash_password("passwordA1")))
            db.commit()
        res = self.post("register", {"email": "legacy@example.com", "password": "passwordB1"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["detail"], "Email already registered")
        self.sender.assert_not_called()
        self.assertEqual(self.client.post("/api/auth/login", data={"username": "legacy@example.com", "password": "passwordA1"}, headers=self.headers).status_code, 200)

    def test_existing_account_conflict_rolls_back_activation(self):
        token = self.start()
        with self.Session() as db:
            db.add(User(email="new@example.com", hashed_password=hash_password("legacyPassword1")))
            db.commit()
        self.assertEqual(self.verify(token).status_code, 400)
        with self.Session() as db:
            self.assertEqual(db.query(User).count(), 1)
            self.assertTrue(verify_password("legacyPassword1", db.query(User).one().hashed_password))
            self.assertIsNone(db.query(PendingRegistration).one().consumed_at)

    def test_unknown_malformed_cross_purpose_and_untrusted_requests(self):
        token = self.start()
        self.assertEqual(self.verify("x" * 43).status_code, 400)
        self.assertEqual(self.verify(token, "123").status_code, 422)
        self.assertEqual(self.post("verify-otp", {"email": "new@example.com", "code": "123456"}).status_code, 400)
        self.assertEqual(self.post("reset-password", {"reset_ticket": token, "new_password": "passwordB1"}).status_code, 400)
        with self.Session() as db:
            db.query(PendingRegistration).one().code_hash = registration.hash_otp_code("123456")
            db.commit()
        self.assertEqual(self.verify(token).status_code, 400)
        for path, body in [("register", {"email": "new@example.com", "password": "passwordA1"}),
                           ("verify-registration", {"registration_token": token, "code": "123456"}),
                           ("resend-registration", {"registration_token": token})]:
            self.assertEqual(self.client.post("/api/auth/" + path, json=body).status_code, 403)

    def test_invalid_email_and_password_are_rejected_without_sending(self):
        for email, password in [("a@@example.com", "passwordA1"), ("a b@example.com", "passwordA1"),
                                ("new@example.com", "short"), ("new@example.com", "ก" * 25)]:
            self.assertEqual(self.post("register", {"email": email, "password": password}).status_code, 400)
        self.sender.assert_not_called()

    def test_expired_window_rejects_old_token_and_allows_fresh_registration(self):
        token = self.start()
        self.age(window_started_at=datetime.now(timezone.utc) - timedelta(hours=2),
                 last_sent_at=datetime.now(timezone.utc) - timedelta(hours=2), attempts=5, send_count=5)
        self.assertEqual(self.verify(token).status_code, 400)
        self.assertEqual(self.post("resend-registration", {"registration_token": token}).status_code, 400)
        new_token = self.start()
        self.assertEqual(self.verify(new_token).status_code, 200)

    def test_busy_postgres_lock_returns_immediately_and_uses_bound_key(self):
        db = Mock()
        db.get_bind.return_value.dialect.name = "postgresql"
        db.execute.return_value.scalar_one.return_value = False
        with self.assertRaises(HTTPException) as caught:
            registration.lock_email(db, "new@example.com")
        self.assertEqual(caught.exception.status_code, 429)
        statement, params = db.execute.call_args.args
        self.assertIn("pg_try_advisory_xact_lock(:key)", str(statement))
        self.assertIsInstance(params["key"], int)
        db.execute.return_value.scalar_one.return_value = True
        registration.lock_email(db, "new@example.com")
        self.assertEqual(db.execute.call_args.args[1], params)

    def test_migration_and_model_have_same_columns_and_uniqueness(self):
        path = Path(__file__).parents[1] / "alembic/versions/20261022_pending_registrations.py"
        spec = importlib.util.spec_from_file_location("registration_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()
            view = inspect(conn)
            self.assertEqual({col["name"] for col in view.get_columns("pending_registrations")}, set(PendingRegistration.__table__.columns.keys()))
            self.assertEqual({tuple(c["column_names"]) for c in view.get_unique_constraints("pending_registrations")}, {("email",), ("registration_token_hash",)})
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
