import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, User, UserIngredient
from fridge_repository import delete_user_ingredient, insert_user_ingredient, list_user_ingredients


class FridgeRepositoryTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine, tables=[User.__table__, UserIngredient.__table__])
        self.db = Session(engine)
        user = User(email="test@example.com")
        self.db.add(user)
        self.db.commit()
        self.user_id = user.id

    def tearDown(self):
        self.db.close()

    def test_legacy_quantity_is_preserved_but_not_exposed(self):
        row = UserIngredient(
            user_id=self.user_id, name="egg", category="Other", quantity="12 pieces", image="egg.png"
        )
        self.db.add(row)
        self.db.commit()

        result = list_user_ingredients(self.db, self.user_id)

        self.assertEqual(result[0]["name"], "egg")
        self.assertNotIn("quantity", result[0])
        stored = self.db.get(UserIngredient, result[0]["id"])
        self.assertEqual(stored.quantity, "12 pieces")

    def test_new_presence_row_stores_null_quantity(self):
        result = insert_user_ingredient(
            self.db,
            user_id=self.user_id,
            name="holy basil leaves",
            category="Vegetables",
            image="basil.png",
        )

        self.assertNotIn("quantity", result)
        stored = self.db.get(UserIngredient, result["id"])
        self.assertIsNone(stored.quantity)

    def test_delete_scopes_to_owning_user(self):
        other_user = User(email="other@example.com")
        self.db.add(other_user)
        self.db.commit()

        created = insert_user_ingredient(
            self.db, user_id=self.user_id, name="tofu", category="Other", image=None
        )

        self.assertFalse(
            delete_user_ingredient(self.db, user_id=other_user.id, ingredient_id=created["id"])
        )
        self.assertTrue(
            delete_user_ingredient(self.db, user_id=self.user_id, ingredient_id=created["id"])
        )

    def test_insert_stores_and_exposes_expiry_date(self):
        expiry = date.today() + timedelta(days=5)
        result = insert_user_ingredient(
            self.db,
            user_id=self.user_id,
            name="milk",
            category="Other",
            image=None,
            expiry_date=expiry,
        )
        self.assertEqual(result["expiry_date"], expiry.isoformat())

    def test_insert_without_expiry_date_exposes_null(self):
        result = insert_user_ingredient(
            self.db, user_id=self.user_id, name="rice", category="Other", image=None
        )
        self.assertIsNone(result["expiry_date"])

    def test_list_orders_by_nearest_expiry_first_nulls_last(self):
        today = date.today()
        # Inserted deliberately out of the order they should come back in,
        # so the test can't pass on insertion order alone.
        insert_user_ingredient(
            self.db, user_id=self.user_id, name="no-expiry-item", category="Other", image=None
        )
        insert_user_ingredient(
            self.db,
            user_id=self.user_id,
            name="expires-later",
            category="Other",
            image=None,
            expiry_date=today + timedelta(days=10),
        )
        insert_user_ingredient(
            self.db,
            user_id=self.user_id,
            name="already-expired",
            category="Other",
            image=None,
            expiry_date=today - timedelta(days=1),
        )
        insert_user_ingredient(
            self.db,
            user_id=self.user_id,
            name="expires-soonest",
            category="Other",
            image=None,
            expiry_date=today + timedelta(days=1),
        )

        result = list_user_ingredients(self.db, self.user_id)

        self.assertEqual(
            [r["name"] for r in result],
            ["already-expired", "expires-soonest", "expires-later", "no-expiry-item"],
        )


if __name__ == "__main__":
    unittest.main()
