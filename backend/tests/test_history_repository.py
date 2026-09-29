import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import Base, BaseRecipe, Favorite, GenerateHistory, Rating, User

HISTORY_TABLES = [
    User.__table__,
    BaseRecipe.__table__,
    GenerateHistory.__table__,
    Rating.__table__,
    Favorite.__table__,
]


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=HISTORY_TABLES)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def make_user(db, email):
    user = User(email=email, hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class HistorySchemaTests(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.user = make_user(self.db, "schema@example.com")

    def tearDown(self):
        self.db.close()

    def test_generate_history_round_trips_on_sqlite(self):
        row = GenerateHistory(
            user_id=self.user.id,
            source="generated",
            recipe_name="Thai Basil Pork",
            adjusted_ingredients=["หมูสับ 200 กรัม"],
            diet_tags=["Thai"],
            instructions=["1. ผัดหมู"],
            nutrition={"calories": 420},
            recipe_data={"recipe_name": "Thai Basil Pork", "servings": 2},
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)

        self.assertEqual(row.adjusted_ingredients, ["หมูสับ 200 กรัม"])
        self.assertEqual(row.recipe_data, {"recipe_name": "Thai Basil Pork", "servings": 2})
        self.assertIsNone(row.embedding)

    def test_recipe_data_defaults_to_empty_dict(self):
        row = GenerateHistory(user_id=self.user.id, source="generated", recipe_name="X")
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        self.assertEqual(row.recipe_data, {})

    def test_rating_stores_tag_feedback_and_updated_at(self):
        history = GenerateHistory(user_id=self.user.id, source="generated", recipe_name="X")
        self.db.add(history)
        self.db.commit()
        rating = Rating(
            user_id=self.user.id,
            generate_history_id=history.id,
            stars=5,
            tag="Great",
            feedback="เผ็ดกำลังดี",
        )
        self.db.add(rating)
        self.db.commit()
        self.db.refresh(rating)

        self.assertEqual(rating.tag, "Great")
        self.assertEqual(rating.feedback, "เผ็ดกำลังดี")
        self.assertIsNotNone(rating.updated_at)

from copy import deepcopy

APPROVED = {
    "recipe_name": "Thai Basil Pork",
    "servings": 2,
    "adjusted_ingredients": ["หมูสับ 200 กรัม", "น้ำมัน 1 ช้อนโต๊ะ"],
    "diet_tags": ["Thai"],
    "nutrition": {"basis": "per_serving", "calories": 1.0, "protein_g": 1.0, "carbs_g": 1.0, "fat_g": 1.0},
    "instructions": ["1. ผัดหมู"],
    "safety_warning": "ระวังความร้อน",
    "computed_nutrition": {"basis": "per_serving", "calories": 1.0},
    "nutrition_partially_estimated": False,
}


class InsertGenerateHistoryTests(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.user = make_user(self.db, "writer@example.com")
        self.db.add(BaseRecipe(id=5, name="กะเพรา", image="images/kaprao.png", tags=[], ingredients=[], nutrition={}, instructions=[]))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _insert(self, request_recipe):
        from history_repository import insert_generate_history
        return insert_generate_history(
            self.db, user_id=self.user.id, request_recipe=request_recipe, final_output=deepcopy(APPROVED)
        )

    def test_existing_base_recipe_id_is_linked(self):
        row = self.db.get(GenerateHistory, self._insert({"id": 5, "name": "กะเพรา"}))
        self.assertEqual(row.base_recipe_id, 5)
        self.assertEqual(row.source, "generated")

    def test_unusable_base_recipe_ids_become_null(self):
        # Out-of-INTEGER-range ids (2**70, 2147483648) must be rejected before
        # db.get, or Postgres raises DataError and the whole insert is lost.
        unusable = (
            {"name": "Custom Recipe from Fridge"},
            {"id": 999},
            {"id": "5"},
            {"id": True},
            {"id": 2**70},
            {"id": 2147483648},
            {"id": 0},
            {"id": -1},
        )
        for recipe in unusable:
            with self.subTest(recipe=recipe):
                row = self.db.get(GenerateHistory, self._insert(recipe))
                self.assertIsNone(row.base_recipe_id)

    def test_copies_approved_output(self):
        row = self.db.get(GenerateHistory, self._insert({"name": "Custom"}))
        self.assertEqual(row.user_id, self.user.id)
        self.assertEqual(row.recipe_name, "Thai Basil Pork")
        self.assertEqual(row.adjusted_ingredients, APPROVED["adjusted_ingredients"])
        self.assertEqual(row.diet_tags, ["Thai"])
        self.assertEqual(row.instructions, ["1. ผัดหมู"])
        self.assertEqual(row.nutrition, APPROVED["nutrition"])
        self.assertEqual(row.recipe_data, APPROVED)


class ListHistoryTests(unittest.TestCase):
    def setUp(self):
        from history_repository import insert_generate_history
        self.db = make_session()
        self.alice = make_user(self.db, "alice@example.com")
        self.bob = make_user(self.db, "bob@example.com")
        self.db.add(BaseRecipe(id=5, name="กะเพรา", image="images/kaprao.png", tags=[], ingredients=[], nutrition={}, instructions=[]))
        self.db.commit()
        self.first = insert_generate_history(self.db, user_id=self.alice.id, request_recipe={"id": 5}, final_output=deepcopy(APPROVED))
        self.second = insert_generate_history(self.db, user_id=self.alice.id, request_recipe={"name": "Custom"}, final_output=deepcopy(APPROVED))
        self.bobs = insert_generate_history(self.db, user_id=self.bob.id, request_recipe={"name": "Custom"}, final_output=deepcopy(APPROVED))

    def tearDown(self):
        self.db.close()

    def test_lists_only_own_rows_newest_first(self):
        from history_repository import list_history
        ids = [row["id"] for row in list_history(self.db, self.alice.id)]
        # Same-second created_at on SQLite: the id DESC tiebreak decides.
        self.assertEqual(ids, [self.second, self.first])

    def test_row_shape_image_rating_and_favorite(self):
        from history_repository import list_history
        self.db.add(Rating(user_id=self.alice.id, generate_history_id=self.first, stars=4,
                           tag="Tasty", feedback="เผ็ดไป 🌶️ → ลดพริก"))
        self.db.add(Favorite(user_id=self.alice.id, generate_history_id=self.first))
        self.db.commit()

        rows = {row["id"]: row for row in list_history(self.db, self.alice.id)}
        first, second = rows[self.first], rows[self.second]

        self.assertEqual(first["image"], "http://localhost:8000/images/kaprao.png")
        self.assertEqual(first["rating"], {"stars": 4, "tag": "Tasty", "feedback": "เผ็ดไป 🌶️ → ลดพริก"})
        self.assertTrue(first["is_favorite"])
        self.assertEqual(first["recipe_data"], APPROVED)
        self.assertEqual(first["diet_tags"], ["Thai"])
        self.assertEqual(first["recipe_name"], "Thai Basil Pork")
        self.assertIsInstance(first["created_at"], str)

        self.assertIsNone(second["image"])
        self.assertIsNone(second["rating"])
        self.assertFalse(second["is_favorite"])


class SetFavoriteTests(unittest.TestCase):
    def setUp(self):
        from history_repository import insert_generate_history
        self.db = make_session()
        self.alice = make_user(self.db, "alice@example.com")
        self.history = insert_generate_history(
            self.db, user_id=self.alice.id, request_recipe={"name": "Custom"}, final_output=deepcopy(APPROVED)
        )

    def tearDown(self):
        self.db.close()

    def test_unfavorite_survives_row_already_deleted_by_another_session(self):
        # Behavior pin for the double-DELETE race: the unfavorite must be one
        # atomic DELETE, not load-then-db.delete (which raises StaleDataError
        # when another session deleted the row in between).
        from history_repository import list_history, set_favorite
        self.assertTrue(set_favorite(self.db, user_id=self.alice.id, history_id=self.history, favorite=True))
        loaded = self.db.execute(select(Favorite)).scalar_one()  # now in this session's identity map
        self.assertIsNotNone(loaded)

        other = sessionmaker(bind=self.db.get_bind(), autoflush=False, autocommit=False)()
        try:
            other.execute(delete(Favorite))
            other.commit()
        finally:
            other.close()

        self.assertTrue(set_favorite(self.db, user_id=self.alice.id, history_id=self.history, favorite=False))
        self.assertFalse(list_history(self.db, self.alice.id)[0]["is_favorite"])


if __name__ == "__main__":
    unittest.main()
