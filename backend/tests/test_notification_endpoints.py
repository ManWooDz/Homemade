import os
import sys
import unittest
from datetime import date
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from auth import get_current_user
from database.db import get_db
from database.models import Base, User, UserIngredient
from main import app
from test_notification_repository import TABLES


class NotificationEndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=TABLES)
        with Session(self.engine) as db:
            owner = User(email="owner@example.com")
            other = User(email="other@example.com")
            db.add_all([owner, other])
            db.flush()
            self.owner_id, self.other_id = owner.id, other.id
            db.add(UserIngredient(user_id=owner.id, name="Egg", expiry_date=date(2020, 1, 1)))
            db.commit()
        def get_test_db():
            with Session(self.engine) as db:
                yield db
        def get_test_user():
            with Session(self.engine) as db:
                user = db.get(User, self.owner_id)
                db.expunge(user)
                return user
        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_current_user] = get_test_user
        self.client = TestClient(app)
        self.origin = {"Origin": "http://127.0.0.1:5173"}

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def sync(self):
        return self.client.post("/api/notifications/sync", headers=self.origin)

    def test_sync_feed_read_and_read_all_are_cross_session_persistent(self):
        response = self.sync()
        self.assertEqual(response.status_code, 200)
        record = response.json()["data"]["created_items"][0]
        self.assertEqual(self.sync().json()["data"]["created_items"], [])
        self.assertEqual(self.client.get("/api/notifications").json()["data"]["unread_count"], 1)
        read = self.client.put(f'/api/notifications/{record["id"]}/read', headers=self.origin)
        self.assertIsNotNone(read.json()["data"]["read_at"])
        self.assertEqual(read.json()["unread_count"], 0)
        second = TestClient(app)
        self.assertEqual(second.get("/api/notifications?state=read").json()["data"]["items"][0]["id"], record["id"])
        second.close()
        self.assertEqual(self.client.put("/api/notifications/read-all", headers=self.origin).json()["data"]["unread_count"], 0)

    def test_unknown_or_other_owner_read_returns_404(self):
        record = self.sync().json()["data"]["created_items"][0]
        self.owner_id = self.other_id
        for record_id in (record["id"], 9999):
            self.assertEqual(self.client.put(f"/api/notifications/{record_id}/read", headers=self.origin).status_code, 404)
        self.assertEqual(self.client.get("/api/notifications").json()["data"]["items"], [])

    def test_auth_required_on_all_endpoints(self):
        app.dependency_overrides.pop(get_current_user)
        for method, path in (("get", "/api/notifications"), ("post", "/api/notifications/sync"), ("put", "/api/notifications/read-all"), ("put", "/api/notifications/1/read")):
            self.assertEqual(getattr(self.client, method)(path, headers=self.origin).status_code, 401)

    def test_same_origin_required_on_all_mutations(self):
        for path in ("/api/notifications/sync", "/api/notifications/read-all", "/api/notifications/1/read"):
            method = self.client.post if path.endswith("sync") else self.client.put
            self.assertEqual(method(path, headers={"Origin": "https://untrusted.example"}).status_code, 403)

    def test_invalid_limits_ids_and_state_are_rejected(self):
        for query in ("limit=0", "limit=51", "state=all", "before_id=0", "before_id=2147483648"):
            self.assertEqual(self.client.get("/api/notifications?" + query).status_code, 422)
        for value in ("0", "2147483648", "oops"):
            self.assertEqual(self.client.put(f"/api/notifications/{value}/read", headers=self.origin).status_code, 422)

    def test_failed_sync_or_reads_return_generic_retry_error(self):
        for method, path, target in (
            (self.client.get, "/api/notifications", "list_notifications"),
            (self.client.post, "/api/notifications/sync", "sync_expiry_notifications"),
            (self.client.put, "/api/notifications/read-all", "mark_all_read"),
            (self.client.put, "/api/notifications/1/read", "mark_read"),
        ):
            with patch("main." + target, side_effect=RuntimeError("private-secret")):
                response = method(path, headers=self.origin)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("private-secret", response.text)


if __name__ == "__main__":
    unittest.main()
