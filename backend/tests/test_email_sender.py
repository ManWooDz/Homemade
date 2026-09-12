import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import email_sender


class EmailSenderTests(unittest.TestCase):
    def test_send_otp_email_logs_the_code(self):
        with self.assertLogs(level="INFO") as captured:
            email_sender.send_otp_email("user@example.com", "123456")
        joined = "\n".join(captured.output)
        self.assertIn("user@example.com", joined)
        self.assertIn("123456", joined)


if __name__ == "__main__":
    unittest.main()
