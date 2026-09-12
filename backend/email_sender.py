"""OTP email delivery. Dev fallback logs instead of sending — swapping to
real SMTP later is a change to this one function's body plus new env
vars; no caller needs to change. See
docs/superpowers/specs/2026-09-12-auth-phase3-otp-reset-design.md.
"""

import logging


def send_otp_email(email: str, code: str) -> None:
    logging.info("password reset OTP for %s: %s", email, code)
