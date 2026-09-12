import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import Base, PasswordResetOtp, User


class PasswordResetOtpModelTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine, tables=[User.__table__, PasswordResetOtp.__table__])
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def test_row_defaults_and_nullable_ticket_fields(self):
        db = self.Session()
        user = User(email="model-test@example.com", hashed_password="x")
        db.add(user)
        db.commit()

        import datetime

        row = PasswordResetOtp(
            user_id=user.id,
            code_hash="deadbeef",
            expires_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        self.assertEqual(row.attempts, 0)
        self.assertIsNone(row.consumed_at)
        self.assertIsNone(row.ticket_hash)
        self.assertIsNone(row.ticket_expires_at)
        self.assertIsNone(row.ticket_consumed_at)

    def test_ticket_hash_unique_constraint_allows_multiple_nulls(self):
        db = self.Session()
        user = User(email="nulls-test@example.com", hashed_password="x")
        db.add(user)
        db.commit()

        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        db.add(PasswordResetOtp(user_id=user.id, code_hash="a", expires_at=now))
        db.add(PasswordResetOtp(user_id=user.id, code_hash="b", expires_at=now))
        db.commit()  # must not raise — two rows with ticket_hash=NULL are allowed


if __name__ == "__main__":
    unittest.main()
