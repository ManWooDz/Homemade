import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from auth import get_current_user
from database.db import get_db
from main import app


class PreflightHTTPTests(unittest.TestCase):
    def setUp(self):
        self.overrides = app.dependency_overrides.copy()
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.addCleanup(self.restore_overrides)
        self.headers = {"Origin": "http://127.0.0.1:5173"}

    def restore_overrides(self):
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.overrides)

    def test_new_preflight_requires_authentication_and_same_origin(self):
        response = self.client.post("/api/validate-allergy-preferences",
            json={"preferences": {"allergies": "แพ้งา"}}, headers=self.headers)
        self.assertEqual(response.status_code, 401)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
        response = self.client.post("/api/validate-allergy-preferences",
            json={"preferences": {"allergies": "แพ้งา"}}, headers={"Origin": "https://untrusted.example"})
        self.assertEqual(response.status_code, 403)

    def test_wire_contract_rejects_ambiguity_without_reaching_generation(self):
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
        app.dependency_overrides[get_db] = lambda: MagicMock()
        with patch("main.call_agentic_llm") as provider, patch("main.resolve_blocks_for_request") as graph:
            for allergies, expected in [("แพ้งา", "success"), ("ไม่แพ้นม", "success"), ("ลดแป้ง", "error")]:
                response = self.client.post("/api/validate-allergy-preferences",
                    json={"preferences": {"allergies": allergies}}, headers=self.headers)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], expected)
            generation = self.client.post("/api/generate-recipe-text", headers=self.headers,
                json={"recipe": {"name": "test"}, "ingredients": [{"name": "หมูสับ"}],
                      "preferences": {"allergies": "ลดแป้ง"}})
            self.assertEqual(generation.status_code, 200)
            self.assertEqual(generation.json(), response.json())
            provider.assert_not_called()
            graph.assert_not_called()
        invalid = self.client.post("/api/validate-allergy-preferences", headers=self.headers,
            json={"preferences": {"allergies": ["แพ้งา"]}})
        self.assertEqual(invalid.status_code, 422)


if __name__ == "__main__":
    unittest.main()
