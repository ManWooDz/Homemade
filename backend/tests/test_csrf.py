import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from csrf import verify_same_origin

app = FastAPI()


@app.post("/protected", dependencies=[Depends(verify_same_origin)])
async def protected():
    return {"ok": True}


client = TestClient(app)


class CsrfTests(unittest.TestCase):
    def test_trusted_origin_allowed(self):
        res = client.post("/protected", headers={"Origin": "http://127.0.0.1:5173"})
        self.assertEqual(res.status_code, 200)

    def test_untrusted_origin_rejected(self):
        res = client.post("/protected", headers={"Origin": "http://evil.example"})
        self.assertEqual(res.status_code, 403)

    def test_missing_origin_falls_back_to_referer(self):
        res = client.post("/protected", headers={"Referer": "http://localhost:5173/register"})
        self.assertEqual(res.status_code, 200)

    def test_missing_origin_and_referer_rejected(self):
        res = client.post("/protected")
        self.assertEqual(res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
