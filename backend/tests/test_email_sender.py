import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import email_sender


class EmailSenderTests(unittest.TestCase):
    SMTP_ENV = {
        "EMAIL_BACKEND": "smtp",
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "sender@example.com",
        "SMTP_PASSWORD": "app-password",
        "SMTP_FROM": "HomeMade OTP <sender@example.com>",
    }

    def test_missing_email_backend_configuration_is_rejected(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "EMAIL_BACKEND"):
                email_sender.validate_email_config()

    def test_unknown_email_backend_configuration_is_rejected(self):
        with mock.patch.dict(os.environ, {"EMAIL_BACKEND": "mail"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "console or smtp"):
                email_sender.validate_email_config()

    def test_smtp_backend_requires_all_configuration(self):
        with mock.patch.dict(os.environ, {"EMAIL_BACKEND": "smtp"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SMTP_HOST"):
                email_sender.validate_email_config()

    def test_smtp_backend_requires_a_valid_port(self):
        env = {**self.SMTP_ENV, "SMTP_PORT": "not-a-port"}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SMTP_PORT"):
                email_sender.validate_email_config()

    def test_send_requires_explicit_backend_configuration(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "EMAIL_BACKEND"):
                email_sender.send_otp_email("user@example.com", "123456")

    def test_send_otp_email_logs_the_code(self):
        with mock.patch.dict(os.environ, {"EMAIL_BACKEND": "console"}, clear=True):
            with self.assertLogs(level="INFO") as captured:
                email_sender.send_otp_email("user@example.com", "123456")
        joined = "\n".join(captured.output)
        self.assertIn("user@example.com", joined)
        self.assertIn("123456", joined)

    def test_smtp_backend_sends_a_thai_otp_message_over_starttls(self):
        fake_otp = types.SimpleNamespace(OTP_EXPIRY_MINUTES=10)
        with (
            mock.patch.dict(os.environ, self.SMTP_ENV, clear=True),
            mock.patch.dict(sys.modules, {"otp": fake_otp}),
            mock.patch(
                "email_sender.ssl.create_default_context",
                return_value=mock.sentinel.tls_context,
            ),
            mock.patch("email_sender.smtplib.SMTP") as smtp_class,
        ):
            smtp = smtp_class.return_value.__enter__.return_value
            email_sender.send_otp_email("user@example.com", "123456")

        smtp_class.assert_called_once_with("smtp.gmail.com", 587, timeout=10)
        smtp.starttls.assert_called_once_with(context=mock.sentinel.tls_context)
        smtp.login.assert_called_once_with("sender@example.com", "app-password")
        smtp.send_message.assert_called_once()

        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message["To"], "user@example.com")
        self.assertEqual(message["From"], "HomeMade OTP <sender@example.com>")
        self.assertEqual(message["Subject"], "รหัสยืนยันสำหรับรีเซ็ตรหัสผ่าน Homemade")
        self.assertNotIn("123456", message["Subject"])
        body = message.get_content()
        self.assertIn("123456", body)
        self.assertIn("10 นาที", body)
        self.assertIn("หากคุณไม่ได้เป็นผู้ร้องขอ", body)

    def test_smtp_errors_propagate_without_retry_or_sensitive_logging(self):
        fake_otp = types.SimpleNamespace(OTP_EXPIRY_MINUTES=10)
        errors = (
            email_sender.smtplib.SMTPException("recipient user@example.com rejected"),
            OSError("network failed for user@example.com"),
            TimeoutError("timeout while sending 123456"),
        )
        for error in errors:
            with self.subTest(error_type=type(error).__name__):
                with (
                    mock.patch.dict(os.environ, self.SMTP_ENV, clear=True),
                    mock.patch.dict(sys.modules, {"otp": fake_otp}),
                    mock.patch(
                        "email_sender.ssl.create_default_context",
                        return_value=mock.sentinel.tls_context,
                    ),
                    mock.patch("email_sender.smtplib.SMTP") as smtp_class,
                    self.assertNoLogs(level="INFO"),
                ):
                    smtp = smtp_class.return_value.__enter__.return_value
                    smtp.send_message.side_effect = error
                    with self.assertRaises(type(error)):
                        email_sender.send_otp_email("user@example.com", "123456")

                smtp_class.assert_called_once()
                smtp.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
