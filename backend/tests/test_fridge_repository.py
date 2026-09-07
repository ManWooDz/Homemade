import os
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
