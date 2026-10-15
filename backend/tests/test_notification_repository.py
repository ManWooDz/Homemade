import os
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from uuid import uuid4
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from database.models import Base, BaseRecipe, BaseRecipeFavorite, Favorite, GenerateHistory, Notification, User, UserIngredient
from fridge_repository import delete_user_ingredient, update_user_ingredient
from notification_repository import list_notifications, mark_all_read, mark_read, sync_expiry_notifications

TABLES = [model.__table__ for model in (User, BaseRecipe, BaseRecipeFavorite, GenerateHistory, Favorite, UserIngredient, Notification)]
NOW = datetime(2026, 10, 15, 3, tzinfo=timezone.utc)


class NotificationFixture:
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine, tables=TABLES)
        self.db = Session(self.engine, autoflush=False)
        self.user = User(email="notice@example.com")
        self.other = User(email="other@example.com")
        self.db.add_all([self.user, self.other])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def ingredient(self, expiry, owner=None):
        row = UserIngredient(user_id=owner or self.user.id, name="Egg", expiry_date=expiry)
        self.db.add(row)
        self.db.commit()
        return row

    def sync(self, now=NOW):
        return sync_expiry_notifications(self.db, self.user.id, now=now)

class NotificationRepositoryTests(NotificationFixture, unittest.TestCase):
    def test_three_day_boundary_today_passed_and_missing(self):
        for delta in (-200, -1, 0, 1, 3, 4):
            self.ingredient(date(2026, 10, 15) + timedelta(days=delta))
        self.ingredient(None)
        events = self.sync()["created_items"]
        self.assertEqual(len(events), 5)
        self.assertEqual(sorted(item["kind"] for item in events), ["expiry_near", "expiry_near", "expiry_passed", "expiry_passed", "expiry_today"])

    def test_bangkok_midnight_is_same_event_stage_for_other_device_dates(self):
        self.ingredient(date(2026, 10, 16))
        near = self.sync(datetime(2026, 10, 15, 16, 59, 59, tzinfo=timezone.utc))["created_items"]
        today = self.sync(datetime(2026, 10, 15, 17, 0, tzinfo=timezone.utc))["created_items"]
        self.assertEqual(near[0]["kind"], "expiry_near")
        self.assertEqual(today[0]["kind"], "expiry_today")

    def test_repeat_checks_do_not_recreate_events_or_read_state(self):
        self.ingredient(date(2026, 10, 17))
        event = self.sync()["created_items"][0]
        read = mark_read(self.db, self.user.id, event["id"])
        self.assertEqual(mark_read(self.db, self.user.id, event["id"])["read_at"], read["read_at"])
        self.assertEqual(self.sync()["created_items"], [])
        self.assertEqual(self.sync(NOW + timedelta(days=1))["created_items"], [])
        self.assertEqual(self.sync(NOW + timedelta(days=2))["created_items"][0]["kind"], "expiry_today")
        self.assertEqual(self.sync(NOW + timedelta(days=3))["created_items"][0]["kind"], "expiry_passed")
        self.assertEqual(self.sync(NOW + timedelta(days=4))["created_items"], [])

    def test_first_open_after_gap_does_not_backfill_missed_stages(self):
        self.ingredient(date(2026, 10, 1))
        events = self.sync()["created_items"]
        self.assertEqual([item["kind"] for item in events], ["expiry_passed"])

    def test_ownership_isolation_including_read_all(self):
        self.ingredient(date(2026, 10, 15), self.other.id)
        self.ingredient(date(2026, 10, 15))
        own = self.sync()["created_items"][0]
        other = sync_expiry_notifications(self.db, self.other.id, now=NOW)["created_items"][0]
        self.assertIsNone(mark_read(self.db, self.user.id, other["id"]))
        mark_all_read(self.db, self.user.id)
        self.assertEqual(list_notifications(self.db, self.user.id, state="read")["items"][0]["id"], own["id"])
        self.assertEqual(list_notifications(self.db, self.other.id)["unread_count"], 1)

    def test_pagination_and_read_all_include_unloaded_pages(self):
        for _ in range(25):
            self.ingredient(date(2026, 10, 15))
        self.sync()
        first = list_notifications(self.db, self.user.id)
        second = list_notifications(self.db, self.user.id, before_id=first["next_before_id"])
        self.assertEqual((len(first["items"]), len(second["items"])), (20, 5))
        self.assertEqual(first["unread_count"], 25)
        self.assertFalse(set(row["id"] for row in first["items"]) & set(row["id"] for row in second["items"]))
        self.assertEqual(mark_all_read(self.db, self.user.id)["unread_count"], 0)
        self.assertEqual(list_notifications(self.db, self.user.id, state="read", limit=50)["items"].__len__(), 25)

    def test_date_edit_clear_delete_and_revert_withdraw_without_read_or_deletion(self):
        row = self.ingredient(date(2026, 10, 17))
        event = self.sync()["created_items"][0]
        values = {"name": "Egg", "category": "Other", "expiry_date": date(2026, 11, 1), "quantity_amount": None, "quantity_unit": None}
        update_user_ingredient(self.db, user_id=self.user.id, ingredient_id=row.id, values=values)
        record = self.db.get(Notification, event["id"])
        self.assertIsNotNone(record.withdrawn_at)
        self.assertIsNone(record.read_at)
        self.assertEqual(list_notifications(self.db, self.user.id)["unread_count"], 0)
        values["expiry_date"] = date(2026, 10, 17)
        update_user_ingredient(self.db, user_id=self.user.id, ingredient_id=row.id, values=values)
        self.assertEqual(self.sync()["created_items"], [])
        self.assertEqual(list_notifications(self.db, self.user.id)["items"][0]["id"], event["id"])
        mark_read(self.db, self.user.id, event["id"])
        values["expiry_date"] = None
        update_user_ingredient(self.db, user_id=self.user.id, ingredient_id=row.id, values=values)
        self.assertEqual(list_notifications(self.db, self.user.id, state="read")["items"], [])
        values["expiry_date"] = date(2026, 10, 17)
        update_user_ingredient(self.db, user_id=self.user.id, ingredient_id=row.id, values=values)
        self.sync()
        self.assertEqual(list_notifications(self.db, self.user.id)["unread_count"], 0)
        self.assertTrue(delete_user_ingredient(self.db, user_id=self.user.id, ingredient_id=row.id))
        self.assertEqual(list_notifications(self.db, self.user.id, state="read")["items"], [])
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Notification)), 1)

    def test_concurrent_checks_with_separate_connections_insert_one_occurrence(self):
        evidence = Path(__file__).resolve().parents[2] / "tmp" / "notifications-20261015"
        evidence.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{(evidence / ('concurrency-' + uuid4().hex + '.sqlite')).as_posix()}", connect_args={"timeout": 20})
        Base.metadata.create_all(engine, tables=TABLES)
        with Session(engine) as db:
            owner = User(email="race@example.com")
            db.add(owner)
            db.flush()
            owner_id = owner.id
            db.add(UserIngredient(user_id=owner_id, name="Egg", expiry_date=date(2026, 10, 15)))
            db.commit()
        barrier = Barrier(2)
        def run(_):
            with Session(engine) as db:
                barrier.wait()
                return sync_expiry_notifications(db, owner_id, now=NOW)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, range(2)))
        self.assertEqual(sum(len(result["created_items"]) for result in results), 1)
        with Session(engine) as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(Notification)), 1)
        engine.dispose()

    def test_additive_migration_matches_model_and_refuses_destructive_downgrade(self):
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20261015_add_notifications.py"
        spec = importlib.util.spec_from_file_location("notification_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite:///:memory:")
        User.__table__.create(engine)
        with engine.begin() as connection:
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
        inspector = inspect(engine)
        actual = {column["name"]: column["nullable"] for column in inspector.get_columns("notifications")}
        self.assertEqual(actual, {column.name: column.nullable for column in Notification.__table__.columns})
        self.assertEqual(inspector.get_unique_constraints("notifications")[0]["column_names"], ["user_id", "event_key"])
        self.assertEqual(inspector.get_indexes("notifications")[0]["column_names"], ["user_id", "withdrawn_at", "read_at", "id"])
        self.assertEqual(migration.down_revision, "a8b9c0d1e2f3")
        with self.assertRaises(RuntimeError):
            migration.downgrade()
        self.assertIn("notifications", inspect(engine).get_table_names())
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
