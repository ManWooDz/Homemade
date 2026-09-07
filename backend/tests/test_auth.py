import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jose import jwt

from auth import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    create_access_token,
    hash_password,
    verify_password,
)


class AuthTests(unittest.TestCase):
    def test_hash_and_verify_roundtrip(self):
        hashed = hash_password("correct-horse-battery-staple")
        self.assertTrue(verify_password("correct-horse-battery-staple", hashed))
        self.assertFalse(verify_password("wrong-password", hashed))

    def test_verify_rejects_null_hash(self):
        # hashed_password is nullable (spec.md:17, OAuth-only accounts) —
        # a None hash must fail closed, not throw or pass.
        self.assertFalse(verify_password("anything", None))

    def test_create_access_token_roundtrips_user_id(self):
        token = create_access_token(42)
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        self.assertEqual(payload["sub"], "42")


if __name__ == "__main__":
    unittest.main()
