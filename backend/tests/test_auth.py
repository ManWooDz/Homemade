import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from auth import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    _decode_token,
    _parse_bool_env,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_password,
)
from database.models import Base, RefreshToken, User


class AuthTests(unittest.TestCase):
    def test_hash_and_verify_roundtrip(self):
        hashed = hash_password("correct-horse-battery-staple")
        self.assertTrue(verify_password("correct-horse-battery-staple", hashed))
        self.assertFalse(verify_password("wrong-password", hashed))

    def test_verify_rejects_null_hash(self):
        self.assertFalse(verify_password("anything", None))

    def test_create_access_token_has_type_and_jti(self):
        token = create_access_token(42)
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        self.assertEqual(payload["sub"], "42")
        self.assertEqual(payload["type"], "access")
        self.assertTrue(payload["jti"])

    def test_create_refresh_token_has_type_and_jti(self):
        token = create_refresh_token(42)
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        self.assertEqual(payload["sub"], "42")
        self.assertEqual(payload["type"], "refresh")
        self.assertTrue(payload["jti"])

    def test_tokens_minted_in_same_instant_have_different_jti_and_hash(self):
        # Regression guard: without a random jti, two tokens minted in the
        # same second would be byte-identical, silently breaking rotation
        # uniqueness (this is exactly the bug a design review caught).
        token_a = create_refresh_token(1)
        token_b = create_refresh_token(1)
        self.assertNotEqual(token_a, token_b)
        self.assertNotEqual(hash_token(token_a), hash_token(token_b))

    def test_decode_token_rejects_wrong_type(self):
        access = create_access_token(1)
        self.assertIsNone(_decode_token(access, expected_type="refresh"))

    def test_decode_token_rejects_garbage(self):
        self.assertIsNone(_decode_token("not-a-jwt", expected_type="access"))

    def test_decode_token_rejects_expired(self):
        expired = jwt.encode(
            {
                "sub": "1",
                "type": "access",
                "jti": "x",
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            },
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        self.assertIsNone(_decode_token(expired, expected_type="access"))

    def test_decode_token_rejects_non_numeric_sub(self):
        bad_sub = jwt.encode(
            {
                "sub": "not-a-number",
                "type": "access",
                "jti": "x",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        self.assertIsNone(_decode_token(bad_sub, expected_type="access"))

    def test_decode_token_rejects_missing_jti(self):
        no_jti = jwt.encode(
            {
                "sub": "1",
                "type": "access",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        self.assertIsNone(_decode_token(no_jti, expected_type="access"))

    def test_parse_bool_env_missing_uses_default_false(self):
        os.environ.pop("COOKIE_SECURE_TEST_VAR_UNSET", None)
        self.assertFalse(_parse_bool_env("COOKIE_SECURE_TEST_VAR_UNSET", "false"))

    def test_parse_bool_env_true_string_is_true(self):
        os.environ["COOKIE_SECURE_TEST_VAR"] = "true"
        try:
            self.assertTrue(_parse_bool_env("COOKIE_SECURE_TEST_VAR", "false"))
        finally:
            del os.environ["COOKIE_SECURE_TEST_VAR"]

    def test_parse_bool_env_explicit_false_is_false(self):
        os.environ["COOKIE_SECURE_TEST_VAR"] = "false"
        try:
            self.assertFalse(_parse_bool_env("COOKIE_SECURE_TEST_VAR", "true"))
        finally:
            del os.environ["COOKIE_SECURE_TEST_VAR"]

    def test_missing_jwt_secret_key_fails_fast_on_import(self):
        import importlib
        original = os.environ.get("JWT_SECRET_KEY")
        os.environ["JWT_SECRET_KEY"] = ""
        sys.modules.pop("auth", None)
        try:
            with self.assertRaises(RuntimeError):
                importlib.import_module("auth")
        finally:
            if original is not None:
                os.environ["JWT_SECRET_KEY"] = original
            sys.modules.pop("auth", None)
            importlib.import_module("auth")  # restore for later tests in this run


class RefreshTokenRotationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[User.__table__, RefreshToken.__table__])
        self.db = Session(self.engine)
        user = User(email="rotate@example.com")
        self.db.add(user)
        self.db.commit()
        self.user_id = user.id

    def tearDown(self):
        self.db.close()

    def _seed_refresh_token(self):
        raw = create_refresh_token(self.user_id)
        self.db.add(
            RefreshToken(
                user_id=self.user_id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
        )
        self.db.commit()
        return raw

    def test_rotate_succeeds_once_and_issues_new_pair(self):
        raw = self._seed_refresh_token()
        result = rotate_refresh_token(self.db, raw)
        self.assertIsNotNone(result)
        _new_access, new_refresh = result
        self.assertNotEqual(new_refresh, raw)

    def test_rotate_rejects_replay_of_already_rotated_token(self):
        raw = self._seed_refresh_token()
        first = rotate_refresh_token(self.db, raw)
        self.assertIsNotNone(first)
        second = rotate_refresh_token(self.db, raw)
        self.assertIsNone(second)

    def test_rotate_rejects_unknown_token(self):
        never_seeded = create_refresh_token(self.user_id)
        self.assertIsNone(rotate_refresh_token(self.db, never_seeded))

    def test_rotate_rejects_expired_row_even_if_jwt_not_yet_expired(self):
        # Dual-layer expiry: the JWT's own exp may still be valid, but the
        # DB row's expires_at is the real source of truth for rotation.
        raw = create_refresh_token(self.user_id)
        self.db.add(
            RefreshToken(
                user_id=self.user_id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            )
        )
        self.db.commit()
        self.assertIsNone(rotate_refresh_token(self.db, raw))

    def test_revoke_marks_row_revoked(self):
        raw = self._seed_refresh_token()
        revoke_refresh_token(self.db, raw)
        row = self.db.query(RefreshToken).filter_by(token_hash=hash_token(raw)).first()
        self.assertIsNotNone(row.revoked_at)

    def test_revoke_is_a_no_op_for_unknown_token(self):
        # Must not raise — logout must succeed even with a garbage cookie.
        revoke_refresh_token(self.db, "garbage-not-a-real-token")


if __name__ == "__main__":
    unittest.main()
