"""Password-reset OTP delivery through an explicitly selected backend."""

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

from dotenv import load_dotenv


load_dotenv()


def validate_email_config() -> None:
    backend = os.getenv("EMAIL_BACKEND")
    if backend not in {"console", "smtp"}:
        raise RuntimeError("EMAIL_BACKEND must be set to console or smtp")
    if backend == "smtp":
        required = ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise RuntimeError(f"missing SMTP configuration: {', '.join(missing)}")
        try:
            port = int(os.environ["SMTP_PORT"])
        except ValueError as exc:
            raise RuntimeError("SMTP_PORT must be an integer between 1 and 65535") from exc
        if not 1 <= port <= 65535:
            raise RuntimeError("SMTP_PORT must be an integer between 1 and 65535")


def send_otp_email(email: str, code: str) -> None:
    validate_email_config()
    if os.environ["EMAIL_BACKEND"] == "console":
        logging.info("password reset OTP for %s: %s", email, code)
        return

    from otp import OTP_EXPIRY_MINUTES

    message = EmailMessage()
    message["To"] = email
    message["From"] = os.environ["SMTP_FROM"]
    message["Subject"] = "รหัสยืนยันสำหรับรีเซ็ตรหัสผ่าน Homemade"
    message.set_content(
        "รหัสยืนยันสำหรับรีเซ็ตรหัสผ่านของคุณคือ:\n\n"
        f"{code}\n\n"
        f"รหัสนี้มีอายุ {OTP_EXPIRY_MINUTES} นาที\n"
        "หากคุณไม่ได้เป็นผู้ร้องขอ โปรดเพิกเฉยต่ออีเมลฉบับนี้"
    )

    with smtplib.SMTP(
        os.environ["SMTP_HOST"],
        int(os.environ["SMTP_PORT"]),
        timeout=10,
    ) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)
