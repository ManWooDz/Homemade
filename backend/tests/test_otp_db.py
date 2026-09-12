import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import otp
from database.models import Base, PasswordResetOtp, User


class OtpDbTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine, tables=[User.__table__, PasswordResetOtp.__table__])
        Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.db = Session()
        user = User(email="otpdb@example.com", hashed_password="x")
        self.db.add(user)
        self.db.commit()
        self.user_id = user.id

    def tearDown(self):
        self.db.close()

    def test_create_otp_for_user_returns_row_and_raw_code(self):
        row, code = otp.create_otp_for_user(self.db, self.user_id)
        self.db.commit()
        self.assertEqual(len(code), 6)
        self.assertEqual(row.code_hash, otp.hash_otp_code(code))
        self.assertIsNone(row.consumed_at)

    def test_create_otp_for_user_invalidates_prior_active_row(self):
        first_row, _ = otp.create_otp_for_user(self.db, self.user_id)
        self.db.commit()
        first_id = first_row.id

        second_row, _ = otp.create_otp_for_user(self.db, self.user_id)
        self.db.commit()

        refreshed_first = self.db.get(PasswordResetOtp, first_id)
        now = datetime.now(timezone.utc)
        self.assertLessEqual(
            refreshed_first.expires_at.replace(tzinfo=timezone.utc)
            if refreshed_first.expires_at.tzinfo is None
            else refreshed_first.expires_at,
            now,
        )
        self.assertNotEqual(first_id, second_row.id)

    def test_get_recent_otp_request_respects_window(self):
        row, _ = otp.create_otp_for_user(self.db, self.user_id)
        self.db.commit()

        found = otp.get_recent_otp_request(self.db, self.user_id, seconds=60)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, row.id)

        not_found = otp.get_recent_otp_request(self.db, self.user_id, seconds=0)
        self.assertIsNone(not_found)

    def test_get_recent_otp_request_still_blocks_after_attempt_cap_invalidation(self):
        # Regression for the attempt-cap-bypass-via-resend bug: a row
        # invalidated by the 5-attempt cap (expires_at forced to now) must
        # still be visible to the cooldown check — it only ignores
        # consumed_at/expires_at, not created_at.
        row, code = otp.create_otp_for_user(self.db, self.user_id)
        self.db.commit()
        wrong = "000000" if code != "000000" else "111111"

        for _ in range(5):
            otp.attempt_verify_otp(self.db, self.user_id, wrong)

        refreshed = self.db.get(PasswordResetOtp, row.id)
        self.assertEqual(refreshed.attempts, 5)

        found = otp.get_recent_otp_request(self.db, self.user_id, seconds=60)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, row.id)

    def test_consume_reset_ticket_fails_when_ticket_expired(self):
        _, code = otp.create_otp_for_user(self.db, self.user_id)
        self.db.commit()
        ticket = otp.attempt_verify_otp(self.db, self.user_id, code)
        self.assertIsNotNone(ticket)

        # Backdate ticket_expires_at directly via the test's DB session to
        # simulate an expired reset ticket.
        row = self.db.query(PasswordResetOtp).filter_by(user_id=self.user_id).one()
        row.ticket_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.db.commit()

        result = otp.consume_reset_ticket(self.db, ticket)
        self.assertIsNone(result)

    # "concurrent-verify race safety" (real multi-threaded contention on
    # attempt_verify_otp) is deliberately NOT covered here — genuinely hard
    # to exercise reliably under SQLite+StaticPool (single shared connection
    # serializes writes, so a real race can't be forced the way it could
    # against Postgres). Deferred, not silently missing.

    def test_attempt_verify_otp_succeeds_with_correct_code(self):
        row, code = otp.create_otp_for_user(self.db, self.user_id)
        self.db.commit()

        ticket = otp.attempt_verify_otp(self.db, self.user_id, code)
        self.assertIsNotNone(ticket)

        refreshed = self.db.get(PasswordResetOtp, row.id)
        self.assertIsNotNone(refreshed.consumed_at)
        self.assertEqual(refreshed.ticket_hash, otp.hash_reset_ticket(ticket))

    def test_attempt_verify_otp_fails_with_wrong_code_and_increments_attempts(self):
        row, code = otp.create_otp_for_user(self.db, self.user_id)
        self.db.commit()

        result = otp.attempt_verify_otp(self.db, self.user_id, "000000" if code != "000000" else "111111")
        self.assertIsNone(result)

        refreshed = self.db.get(PasswordResetOtp, row.id)
        self.assertEqual(refreshed.attempts, 1)
        self.assertIsNone(refreshed.consumed_at)

    def test_fifth_wrong_attempt_invalidates_row(self):
        row, code = otp.create_otp_for_user(self.db, self.user_id)
        self.db.commit()
        wrong = "000000" if code != "000000" else "111111"

        for _ in range(5):
            otp.attempt_verify_otp(self.db, self.user_id, wrong)

        refreshed = self.db.get(PasswordResetOtp, row.id)
        self.assertEqual(refreshed.attempts, 5)

        # Even the correct code must now fail — row is dead.
        ticket = otp.attempt_verify_otp(self.db, self.user_id, code)
        self.assertIsNone(ticket)

    def test_attempt_verify_otp_returns_none_when_no_active_row(self):
        result = otp.attempt_verify_otp(self.db, self.user_id, "123456")
        self.assertIsNone(result)

    def test_consume_reset_ticket_succeeds_once(self):
        _, code = otp.create_otp_for_user(self.db, self.user_id)
        self.db.commit()
        ticket = otp.attempt_verify_otp(self.db, self.user_id, code)

        user_id = otp.consume_reset_ticket(self.db, ticket)
        self.db.commit()
        self.assertEqual(user_id, self.user_id)

    def test_consume_reset_ticket_fails_on_reuse(self):
        _, code = otp.create_otp_for_user(self.db, self.user_id)
        self.db.commit()
        ticket = otp.attempt_verify_otp(self.db, self.user_id, code)

        first = otp.consume_reset_ticket(self.db, ticket)
        self.db.commit()
        self.assertEqual(first, self.user_id)

        second = otp.consume_reset_ticket(self.db, ticket)
        self.assertIsNone(second)

    def test_consume_reset_ticket_fails_for_unknown_ticket(self):
        result = otp.consume_reset_ticket(self.db, "not-a-real-ticket")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
