"""OTP generation/hashing and reset-ticket helpers for Phase 3 password
reset. See docs/superpowers/specs/2026-09-12-auth-phase3-otp-reset-design.md.
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, update
from sqlalchemy.orm import Session

from database.models import PasswordResetOtp

OTP_HMAC_SECRET = os.getenv("OTP_HMAC_SECRET")

if not OTP_HMAC_SECRET or len(OTP_HMAC_SECRET.encode("utf-8")) < 32:
    raise RuntimeError(
        "OTP_HMAC_SECRET missing or too short (<32 bytes) in backend/.env — "
        "generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

OTP_HMAC_SECRET_BYTES = OTP_HMAC_SECRET.encode("utf-8")

OTP_EXPIRY_MINUTES = 10
TICKET_EXPIRY_MINUTES = 10
RESEND_COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 5


def generate_otp_code() -> str:
    """Cryptographically secure 6-digit code — secrets, never random."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp_code(code: str) -> str:
    """HMAC-SHA256 keyed by OTP_HMAC_SECRET — plain SHA-256 is unsafe here
    because the 6-digit keyspace (1,000,000 values) is brute-forceable
    offline from a leaked hash."""
    return hmac.new(OTP_HMAC_SECRET_BYTES, code.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_reset_ticket() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_ticket(ticket: str) -> str:
    """Plain SHA-256 — safe here because the ticket is a high-entropy
    token, not a 6-digit code."""
    return hashlib.sha256(ticket.encode("utf-8")).hexdigest()


def get_active_otp_created_within(db: Session, user_id: int, seconds: int) -> PasswordResetOtp | None:
    """Read-only. Used for the resend cooldown check."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=seconds)
    return (
        db.query(PasswordResetOtp)
        .filter(
            PasswordResetOtp.user_id == user_id,
            PasswordResetOtp.consumed_at.is_(None),
            PasswordResetOtp.expires_at > now,
            PasswordResetOtp.created_at > cutoff,
        )
        .first()
    )


def create_otp_for_user(db: Session, user_id: int) -> tuple[PasswordResetOtp, str]:
    """Invalidates any other active OTP for user_id (only one OTP is ever
    valid at a time), inserts a new row, and flushes — does NOT commit.
    The forgot-password endpoint commits only after send_otp_email
    succeeds, so a delivery failure can be rolled back without leaving a
    row that falsely enforces the resend cooldown."""
    now = datetime.now(timezone.utc)
    # synchronize_session=False: without it, SQLAlchemy's default
    # synchronize_session="evaluate" re-evaluates this UPDATE's WHERE
    # clause in pure Python against any matching row already loaded into
    # the session's identity map. SQLite round-trips DateTime(timezone=True)
    # columns as naive datetimes, while `now` here is
    # datetime.now(timezone.utc) — aware — so that Python-side re-evaluation
    # raises "TypeError: can't compare offset-naive and offset-aware
    # datetimes" whenever a matching row is already resident in the
    # session (e.g. a prior db.query(...).first() in the same request).
    # This flag only disables that auxiliary in-memory attribute re-sync;
    # none of the DB-backed functions in this file rely on it (they read
    # results via .returning() or an explicit re-fetch/db.get() instead).
    # The atomic-safety guarantee is unaffected — it comes entirely from
    # the SQL WHERE clause (and .returning() where used), not from this
    # option. Do not remove this without re-testing against the SQLite
    # in-memory test suite (backend/tests/test_otp_db.py) — see the same
    # note at each of the other three .execution_options(synchronize_session=False)
    # call sites in this file.
    db.execute(
        update(PasswordResetOtp)
        .where(
            PasswordResetOtp.user_id == user_id,
            PasswordResetOtp.consumed_at.is_(None),
            PasswordResetOtp.expires_at > now,
        )
        .values(expires_at=now)
        .execution_options(synchronize_session=False)
    )
    code = generate_otp_code()
    row = PasswordResetOtp(
        user_id=user_id,
        code_hash=hash_otp_code(code),
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(row)
    db.flush()
    return row, code


def attempt_verify_otp(db: Session, user_id: int, code: str) -> str | None:
    """Self-contained: commits internally on both the success and failure
    paths (mirrors auth.rotate_refresh_token — no cross-cutting
    transaction requirement forces this open, unlike consume_reset_ticket
    below). The two-step atomic-UPDATE approach (attempt the success
    UPDATE first, only issue the attempt-increment UPDATE if it affected
    no row) is what makes this race-safe under concurrent requests rather
    than a read-then-write check."""
    now = datetime.now(timezone.utc)
    row = (
        db.query(PasswordResetOtp)
        .filter(
            PasswordResetOtp.user_id == user_id,
            PasswordResetOtp.consumed_at.is_(None),
            PasswordResetOtp.expires_at > now,
        )
        .first()
    )
    if row is None:
        return None

    ticket = generate_reset_ticket()
    # synchronize_session=False: this row was just loaded above via
    # db.query(...).first(), so it IS in the identity map — see the
    # naive/aware datetime note in create_otp_for_user for why this
    # matters here and must not be dropped.
    result = db.execute(
        update(PasswordResetOtp)
        .where(
            PasswordResetOtp.id == row.id,
            PasswordResetOtp.consumed_at.is_(None),
            PasswordResetOtp.expires_at > now,
            PasswordResetOtp.attempts < MAX_ATTEMPTS,
            PasswordResetOtp.code_hash == hash_otp_code(code),
        )
        .values(
            consumed_at=now,
            ticket_hash=hash_reset_ticket(ticket),
            ticket_expires_at=now + timedelta(minutes=TICKET_EXPIRY_MINUTES),
        )
        .returning(PasswordResetOtp.user_id)
        .execution_options(synchronize_session=False)
    )
    if result.first() is not None:
        db.commit()
        return ticket

    # synchronize_session=False: same reason as above — see
    # create_otp_for_user's note.
    db.execute(
        update(PasswordResetOtp)
        .where(
            PasswordResetOtp.id == row.id,
            PasswordResetOtp.consumed_at.is_(None),
            PasswordResetOtp.expires_at > now,
            PasswordResetOtp.attempts < MAX_ATTEMPTS,
        )
        .values(
            attempts=PasswordResetOtp.attempts + 1,
            expires_at=case(
                (PasswordResetOtp.attempts + 1 >= MAX_ATTEMPTS, now),
                else_=PasswordResetOtp.expires_at,
            ),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return None


def consume_reset_ticket(db: Session, ticket: str) -> int | None:
    """Does NOT commit — the reset-password endpoint must commit this
    together with the password update and refresh-token revocation so all
    three writes succeed or roll back as one transaction."""
    now = datetime.now(timezone.utc)
    # synchronize_session=False: no row is pre-loaded here, so this
    # particular call site wouldn't hit the naive/aware TypeError today —
    # kept for consistency with the other three update() calls in this
    # file and to stay safe if a future caller pre-loads the row before
    # calling this function. See create_otp_for_user's note for the full
    # explanation.
    result = db.execute(
        update(PasswordResetOtp)
        .where(
            PasswordResetOtp.ticket_hash == hash_reset_ticket(ticket),
            PasswordResetOtp.ticket_consumed_at.is_(None),
            PasswordResetOtp.ticket_expires_at > now,
        )
        .values(ticket_consumed_at=now)
        .returning(PasswordResetOtp.user_id)
        .execution_options(synchronize_session=False)
    )
    row = result.first()
    if row is None:
        db.rollback()
        return None
    return row[0]
