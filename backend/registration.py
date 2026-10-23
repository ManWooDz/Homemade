"""Registration challenges stay separate from password-reset tickets."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import text, update

from auth import hash_password
from database.models import PendingRegistration, User
from otp import generate_otp_code, hash_otp_code, MAX_ATTEMPTS, OTP_EXPIRY_MINUTES, RESEND_COOLDOWN_SECONDS

SEND_LIMIT = 5
WINDOW = timedelta(hours=1)
INVALID_CODE = "Invalid or expired registration code"
RATE_LIMIT = "Too many registration attempts. Try again later"


def utc(value):
    # SQLite test dates are naive; PostgreSQL stores timezone-aware dates.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def code_hash(token, code):
    return hash_otp_code(f"registration:{token}:{code}")


def lock_email(db, email):
    if db.get_bind().dialect.name == "postgresql":
        # Transaction locks also serialize the first request, before a row exists.
        key = int.from_bytes(hashlib.sha256(f"registration:{email}".encode()).digest()[:8], "big", signed=True)
        if not db.execute(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key}).scalar_one():
            raise HTTPException(429, RATE_LIMIT)


def check_send_limit(row, now):
    if now - utc(row.window_started_at) < WINDOW and (row.send_count >= SEND_LIMIT or row.attempts >= MAX_ATTEMPTS):
        raise HTTPException(429, RATE_LIMIT)
    if now - utc(row.last_sent_at) < timedelta(seconds=RESEND_COOLDOWN_SECONDS):
        raise HTTPException(429, RATE_LIMIT)


def issue_code(row, token, now):
    if now - utc(row.window_started_at) >= WINDOW:
        row.window_started_at, row.send_count, row.attempts = now, 0, 0
    code = generate_otp_code()
    row.code_hash = code_hash(token, code)
    row.last_sent_at = now
    row.expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
    row.send_count += 1
    return code


def prepare_registration(db, email, password):
    lock_email(db, email)
    if db.query(User).filter_by(email=email).first() is not None:
        raise HTTPException(400, "Email already registered")
    now = datetime.now(timezone.utc)
    row = db.query(PendingRegistration).filter_by(email=email).first()
    if row is not None:
        check_send_limit(row, now)
    else:
        row = PendingRegistration(email=email, window_started_at=now, attempts=0, send_count=0)
        db.add(row)
    token = secrets.token_urlsafe(32)
    row.registration_token_hash = token_hash(token)
    row.hashed_password = hash_password(password)
    row.consumed_at = None
    code = issue_code(row, token, now)
    db.flush()
    return row, token, code


def pending_for_token(db, token):
    digest = token_hash(token)
    row = db.query(PendingRegistration).filter_by(registration_token_hash=digest).first()
    if row is None:
        raise HTTPException(400, INVALID_CODE)
    lock_email(db, row.email)
    db.refresh(row)
    if row.registration_token_hash != digest or row.consumed_at is not None:
        raise HTTPException(400, INVALID_CODE)
    if datetime.now(timezone.utc) - utc(row.window_started_at) >= WINDOW:
        raise HTTPException(400, INVALID_CODE)
    return row


def prepare_resend(db, token):
    row = pending_for_token(db, token)
    now = datetime.now(timezone.utc)
    check_send_limit(row, now)
    code = issue_code(row, token, now)
    db.flush()
    return row, code


def verify_registration(db, token, code):
    row = pending_for_token(db, token)
    now = datetime.now(timezone.utc)
    if row.attempts >= MAX_ATTEMPTS or utc(row.expires_at) <= now:
        raise HTTPException(400, INVALID_CODE)
    if not hmac.compare_digest(row.code_hash, code_hash(token, code)):
        db.execute(update(PendingRegistration).where(
            PendingRegistration.id == row.id, PendingRegistration.attempts < MAX_ATTEMPTS,
        ).values(attempts=PendingRegistration.attempts + 1))
        db.commit()
        raise HTTPException(400, INVALID_CODE)
    claimed = db.execute(update(PendingRegistration).where(
        PendingRegistration.id == row.id,
        PendingRegistration.registration_token_hash == token_hash(token),
        PendingRegistration.code_hash == code_hash(token, code),
        PendingRegistration.consumed_at.is_(None),
        PendingRegistration.attempts < MAX_ATTEMPTS,
        PendingRegistration.expires_at > now,
    ).values(consumed_at=now, hashed_password=None, code_hash=None)
        .returning(PendingRegistration.id).execution_options(synchronize_session=False)).first()
    if claimed is None:
        raise HTTPException(400, INVALID_CODE)
    user = User(email=row.email, hashed_password=row.hashed_password)
    db.add(user)
    db.flush()
    return user
