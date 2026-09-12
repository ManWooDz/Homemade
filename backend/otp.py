"""OTP generation/hashing and reset-ticket helpers for Phase 3 password
reset. See docs/superpowers/specs/2026-09-12-auth-phase3-otp-reset-design.md.
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

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
