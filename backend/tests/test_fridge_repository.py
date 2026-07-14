import sqlite3
import unittest

from fridge_repository import insert_user_ingredient, list_user_ingredients


class FridgeRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute(
            """
            CREATE TABLE user_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'Other',
                quantity TEXT DEFAULT '1',
                image TEXT
            )
            """
        )

    def tearDown(self):
        self.conn.close()

    def test_legacy_quantity_is_preserved_but_not_exposed(self):
        self.conn.execute(
            "INSERT INTO user_ingredients (name, category, quantity, image) VALUES (?, ?, ?, ?)",
            ("egg", "Other", "12 pieces", "egg.png"),
        )
        self.conn.commit()

        result = list_user_ingredients(self.conn)

        self.assertEqual(result[0]["name"], "egg")
        self.assertNotIn("quantity", result[0])
        stored = self.conn.execute(
            "SELECT quantity FROM user_ingredients WHERE id = ?", (result[0]["id"],)
        ).fetchone()[0]
        self.assertEqual(stored, "12 pieces")

    def test_new_presence_row_stores_null_quantity(self):
        result = insert_user_ingredient(
            self.conn,
            name="holy basil leaves",
            category="Vegetables",
            image="basil.png",
        )

        self.assertNotIn("quantity", result)
        stored = self.conn.execute(
            "SELECT quantity FROM user_ingredients WHERE id = ?", (result["id"],)
        ).fetchone()[0]
        self.assertIsNone(stored)


if __name__ == "__main__":
    unittest.main()
