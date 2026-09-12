import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

import otp


class OtpCryptoTests(unittest.TestCase):
    def test_generate_otp_code_is_six_digits(self):
        code = otp.generate_otp_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_generate_otp_code_zero_pads(self):
        # Statistically near-certain to produce a code needing padding at
        # least once in a large sample; this just proves the format holds.
        codes = [otp.generate_otp_code() for _ in range(2000)]
        self.assertTrue(any(c.startswith("0") for c in codes))
        self.assertTrue(all(len(c) == 6 for c in codes))

    def test_hash_otp_code_is_deterministic_and_keyed(self):
        h1 = otp.hash_otp_code("123456")
        h2 = otp.hash_otp_code("123456")
        h3 = otp.hash_otp_code("654321")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)
        self.assertEqual(len(h1), 64)  # sha256 hex digest length

    def test_generate_reset_ticket_is_high_entropy_and_unique(self):
        t1 = otp.generate_reset_ticket()
        t2 = otp.generate_reset_ticket()
        self.assertNotEqual(t1, t2)
        self.assertGreater(len(t1), 32)

    def test_hash_reset_ticket_is_deterministic(self):
        h1 = otp.hash_reset_ticket("abc")
        h2 = otp.hash_reset_ticket("abc")
        h3 = otp.hash_reset_ticket("xyz")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)
        self.assertEqual(len(h1), 64)


if __name__ == "__main__":
    unittest.main()
