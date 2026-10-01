import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, delete, null, select, update
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
from dataclasses import FrozenInstanceError
from unittest.mock import patch

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


class HistoryEmbeddingSnapshotTests(unittest.TestCase):
    def setUp(self):
        from history_repository import insert_generate_history
        self.db = make_session()
        self.alice = make_user(self.db, "snapshot-alice@example.com")
        self.bob = make_user(self.db, "snapshot-bob@example.com")
        self.history_id = insert_generate_history(
            self.db, user_id=self.alice.id, request_recipe={}, final_output=deepcopy(APPROVED)
        )

    def tearDown(self):
        self.db.close()

    def snapshot(self, user_id):
        import history_repository
        getter = getattr(history_repository, "get_history_embedding_snapshot", None)
        self.assertTrue(callable(getter), "owned immutable embedding snapshot is missing")
        return getter(self.db, user_id=user_id, history_id=self.history_id)

    def test_owned_snapshot_survives_close_and_is_immutable(self):
        snapshot = self.snapshot(self.alice.id)
        self.db.close()
        self.assertEqual(snapshot.history_id, self.history_id)
        self.assertEqual(snapshot.user_id, self.alice.id)
        self.assertEqual(snapshot.recipe_name, "Thai Basil Pork")
        self.assertEqual(snapshot.adjusted_ingredients, ("หมูสับ 200 กรัม", "น้ำมัน 1 ช้อนโต๊ะ"))
        self.assertEqual(snapshot.diet_tags, ("Thai",))
        self.assertIsNone(snapshot.embedding)
        with self.assertRaises(FrozenInstanceError):
            snapshot.recipe_name = "changed"
        with self.assertRaises(TypeError):
            snapshot.adjusted_ingredients[0] = "changed"

    def test_other_user_cannot_obtain_snapshot(self):
        self.assertIsNone(self.snapshot(self.bob.id))

    def test_snapshot_copies_existing_vector_into_immutable_tuple(self):
        row = self.db.get(GenerateHistory, self.history_id)
        row.embedding = [1.0] + [0.0] * 767
        self.db.commit()
        snapshot = self.snapshot(self.alice.id)
        self.db.close()
        self.assertEqual(snapshot.embedding, (1.0,) + (0.0,) * 767)
        with self.assertRaises(TypeError):
            snapshot.embedding[0] = 0.0


class SetHistoryEmbeddingTests(unittest.TestCase):
    def setUp(self):
        from history_repository import insert_generate_history, upsert_rating
        self.db = make_session()
        alice = make_user(self.db, "vector-alice@example.com")
        bob = make_user(self.db, "vector-bob@example.com")
        self.alice_id, self.bob_id = alice.id, bob.id
        self.history_id = insert_generate_history(
            self.db, user_id=self.alice_id, request_recipe={}, final_output=deepcopy(APPROVED)
        )
        self.other_history_id = insert_generate_history(
            self.db, user_id=self.alice_id, request_recipe={}, final_output=deepcopy(APPROVED)
        )
        self.rating = upsert_rating(
            self.db, user_id=self.alice_id, history_id=self.history_id,
            stars=4, tag="Tasty", feedback="keep this rating",
        )
        # VECTOR on Postgres stores a missing vector as SQL NULL. SQLite's
        # test-only JSON variant otherwise serializes Python None as JSON null.
        self.db.execute(update(GenerateHistory).values(embedding=null()))
        self.db.commit()
        self.db.close()
        self.vector = [1.0] + [0.0] * 767

    def tearDown(self):
        self.db.close()

    def setter(self):
        import history_repository
        setter = getattr(history_repository, "set_history_embedding_if_missing", None)
        self.assertTrue(callable(setter), "conditional embedding update is missing")
        return setter

    def save(self, user_id=None):
        return self.setter()(
            self.db, user_id=self.alice_id if user_id is None else user_id,
            history_id=self.history_id, embedding=self.vector,
        )

    def test_updates_only_owned_missing_vector_and_commits_one_row(self):
        with patch.object(self.db, "commit", wraps=self.db.commit) as commit:
            self.assertTrue(self.save())
            self.assertEqual(commit.call_count, 1)
        with sessionmaker(bind=self.db.get_bind())() as reader:
            self.assertEqual(reader.get(GenerateHistory, self.history_id).embedding, self.vector)
            self.assertIsNone(reader.get(GenerateHistory, self.other_history_id).embedding)
            rating = reader.execute(select(Rating)).scalar_one()
            self.assertEqual((rating.stars, rating.tag, rating.feedback), (4, "Tasty", "keep this rating"))

    def test_update_sql_requires_id_owner_and_null_embedding(self):
        from sqlalchemy import event
        statements = []

        def record(connection, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        engine = self.db.get_bind()
        event.listen(engine, "before_cursor_execute", record)
        try:
            self.assertTrue(self.save())
        finally:
            event.remove(engine, "before_cursor_execute", record)
        updates = [statement for statement in statements if statement.startswith("UPDATE")]
        self.assertEqual(len(updates), 1)
        where = updates[0].split("WHERE", 1)[1]
        self.assertIn("generate_history.id =", where)
        self.assertIn("generate_history.user_id =", where)
        self.assertIn("generate_history.embedding IS NULL", where)

    def test_cross_user_update_is_false_without_commit(self):
        with patch.object(self.db, "commit", wraps=self.db.commit) as commit:
            self.assertFalse(self.save(self.bob_id))
            self.assertEqual(commit.call_count, 0)
        self.assertIsNone(self.db.get(GenerateHistory, self.history_id).embedding)

    def test_concurrent_winner_is_false_without_overwrite_or_commit(self):
        # A stale loaded row still says NULL; another session wins before UPDATE.
        stale = self.db.get(GenerateHistory, self.history_id)
        self.assertIsNone(stale.embedding)
        winner = [0.0, 1.0] + [0.0] * 766
        with sessionmaker(bind=self.db.get_bind())() as other:
            other.get(GenerateHistory, self.history_id).embedding = winner
            other.commit()
        with patch.object(self.db, "commit", wraps=self.db.commit) as commit:
            self.assertFalse(self.save())
            self.assertEqual(commit.call_count, 0)
        self.db.expire_all()
        self.assertEqual(self.db.get(GenerateHistory, self.history_id).embedding, winner)

    def test_commit_failure_rolls_back_vector_and_preserves_rating(self):
        setter = self.setter()
        with patch.object(self.db, "commit", side_effect=RuntimeError("update commit failed")), \
                patch.object(self.db, "rollback", wraps=self.db.rollback) as rollback:
            with self.assertRaises(RuntimeError):
                setter(self.db, user_id=self.alice_id, history_id=self.history_id, embedding=self.vector)
            self.assertEqual(rollback.call_count, 1)
        self.assertIsNone(self.db.get(GenerateHistory, self.history_id).embedding)
        rating = self.db.execute(select(Rating)).scalar_one()
        self.assertEqual((rating.stars, rating.tag, rating.feedback), (4, "Tasty", "keep this rating"))


if __name__ == "__main__":
    unittest.main()
