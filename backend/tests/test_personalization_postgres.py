import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Favorite, GenerateHistory, Rating, User
from personalization.repository import retrieve_similar_signals


@unittest.skipUnless(
    os.getenv("RUN_PG_TESTS") == "1",
    "set RUN_PG_TESTS=1 with docker Postgres running",
)
class PersonalizationRepositoryPostgresTests(unittest.TestCase):
    def setUp(self):
        from database.db import DATABASE_URL

        self.engine = create_engine(DATABASE_URL)
        self.conn = self.engine.connect()
        self.trans = self.conn.begin()
        self.db = Session(bind=self.conn, join_transaction_mode="create_savepoint")

        self.owner = User(email="zz-personalization-owner@example.com", hashed_password="x")
        self.other = User(email="zz-personalization-other@example.com", hashed_password="x")
        self.db.add_all([self.owner, self.other])
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.trans.rollback()
        self.conn.close()
        self.engine.dispose()

    @staticmethod
    def _vector(*components):
        return list(components) + [0.0] * (768 - len(components))

    def _add_signal(self, user_id, name, stars, vector):
        history = GenerateHistory(
            user_id=user_id,
            source="generated",
            recipe_name=name,
            adjusted_ingredients=[name],
            diet_tags=["integration"],
            instructions=[],
            nutrition={},
            recipe_data={},
            embedding=vector,
        )
        self.db.add(history)
        self.db.flush()
        self.db.add(
            Rating(
                user_id=user_id,
                generate_history_id=history.id,
                stars=stars,
                tag="integration",
                feedback=None,
            )
        )
        return history

    def test_pgvector_orders_and_filters_owned_positive_and_negative_pools(self):
        positive_near = self._add_signal(self.owner.id, "positive-near", 5, self._vector(1.0, 0.0))
        positive_far = self._add_signal(self.owner.id, "positive-far", 4, self._vector(0.0, 1.0))
        positive_null = self._add_signal(self.owner.id, "positive-null", 5, None)
        negative_orthogonal = self._add_signal(self.owner.id, "negative-orthogonal", 2, self._vector(0.0, 1.0))
        negative_opposite = self._add_signal(self.owner.id, "negative-opposite", 1, self._vector(-1.0, 0.0))
        other_near = self._add_signal(self.other.id, "other-near", 5, self._vector(1.0, 0.0))
        self.db.add(Favorite(user_id=self.owner.id, generate_history_id=positive_near.id))
        self.db.flush()

        query = self._vector(1.0, 0.0)
        positives = retrieve_similar_signals(self.db, self.owner.id, query, [4, 5])
        negatives = retrieve_similar_signals(self.db, self.owner.id, query, [1, 2])
        limited = retrieve_similar_signals(self.db, self.owner.id, query, [4, 5], limit=1)

        self.assertEqual(
            [signal.history_id for signal in positives],
            [positive_near.id, positive_far.id],
        )
        self.assertEqual(
            [signal.history_id for signal in negatives],
            [negative_orthogonal.id, negative_opposite.id],
        )
        self.assertEqual([signal.history_id for signal in limited], [positive_near.id])
        self.assertTrue(positives[0].is_favorite)
        returned_ids = {signal.history_id for signal in positives + negatives}
        self.assertNotIn(positive_null.id, returned_ids)
        self.assertNotIn(other_near.id, returned_ids)


if __name__ == "__main__":
    unittest.main()
