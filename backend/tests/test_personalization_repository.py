import os
import sys
import unittest
from dataclasses import FrozenInstanceError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.models import Base, Favorite, GenerateHistory, Rating, User
from personalization.repository import (
    HistorySignal,
    count_embedded_signals,
    list_profile_signals,
)


PERSONALIZATION_TABLES = [
    User.__table__,
    GenerateHistory.__table__,
    Rating.__table__,
    Favorite.__table__,
]


class PersonalizationRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine, tables=PERSONALIZATION_TABLES)
        self.db = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)()

        self.owner = User(id=101, email="owner-personalization@example.com", hashed_password="x")
        self.other = User(id=202, email="other-personalization@example.com", hashed_password="x")
        self.db.add_all([self.owner, self.other])

        self._add_signal(11, self.owner.id, 1, embedding=[1.0] + [0.0] * 767)
        self._add_signal(12, self.owner.id, 2, embedding=[0.0, 1.0] + [0.0] * 766)
        self._add_signal(13, self.owner.id, 3, embedding=[0.0, 0.0, 1.0] + [0.0] * 765)
        self._add_signal(14, self.owner.id, 4, embedding=[0.0, 0.0, 0.0, 1.0] + [0.0] * 764)
        self._add_signal(15, self.owner.id, 5, embedding=[0.0, 0.0, 0.0, 0.0, 1.0] + [0.0] * 763)
        self._add_signal(16, self.owner.id, 4, embedding=None)
        self._add_signal(17, self.other.id, 5, embedding=[1.0] + [0.0] * 767)

        # A rating owned by another user must not turn the owner's history row
        # into a signal, even though the history id itself belongs to owner.
        self._add_history(18, self.owner.id, embedding=[1.0] + [0.0] * 767)
        self.db.add(
            Rating(
                user_id=self.other.id,
                generate_history_id=18,
                stars=5,
                tag="Wrong owner",
                feedback="must not leak",
            )
        )

        self.db.add_all(
            [
                Favorite(user_id=self.owner.id, generate_history_id=15),
                Favorite(user_id=self.other.id, generate_history_id=17),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _add_history(self, history_id, user_id, *, embedding):
        self.db.add(
            GenerateHistory(
                id=history_id,
                user_id=user_id,
                source="generated",
                recipe_name=f"Recipe {history_id}",
                adjusted_ingredients=[f"ingredient {history_id}"],
                diet_tags=[f"tag-{history_id}"],
                instructions=[],
                nutrition={},
                recipe_data={},
                embedding=embedding,
            )
        )

    def _add_signal(self, history_id, user_id, stars, *, embedding):
        self._add_history(history_id, user_id, embedding=embedding)
        self.db.add(
            Rating(
                user_id=user_id,
                generate_history_id=history_id,
                stars=stars,
                tag=f"rating-{stars}",
                feedback=f"feedback-{history_id}",
            )
        )

    def test_count_includes_only_owned_non_neutral_rows_with_embeddings(self):
        self.assertEqual(count_embedded_signals(self.db, self.owner.id), 4)
        self.assertEqual(count_embedded_signals(self.db, self.other.id), 1)

    def test_profile_includes_rated_null_vectors_and_joined_favorite_state(self):
        signals = list_profile_signals(self.db, self.owner.id)

        self.assertEqual([signal.history_id for signal in signals], [11, 12, 13, 14, 15, 16])
        self.assertEqual([signal.history_id for signal in signals if signal.is_favorite], [15])
        self.assertEqual(signals[-1].stars, 4)
        self.assertEqual(signals[-1].feedback, "feedback-16")
        self.assertNotIn(17, [signal.history_id for signal in signals])
        self.assertNotIn(18, [signal.history_id for signal in signals])

    def test_profile_query_is_sqlite_compatible_without_unnest(self):
        statements = []

        def capture_statement(_conn, _cursor, statement, _parameters, _context, _executemany):
            statements.append(statement)

        event.listen(self.engine, "before_cursor_execute", capture_statement)
        try:
            list_profile_signals(self.db, self.owner.id)
        finally:
            event.remove(self.engine, "before_cursor_execute", capture_statement)

        self.assertTrue(statements)
        self.assertNotIn("unnest(", "\n".join(statements).lower())

    def test_history_signal_is_immutable(self):
        signal = HistorySignal(
            history_id=1,
            recipe_name="Immutable",
            adjusted_ingredients=("rice",),
            diet_tags=("Thai",),
            stars=5,
            rating_tag="Great",
            feedback="keep this shape stable",
            is_favorite=True,
        )

        with self.assertRaises(FrozenInstanceError):
            signal.stars = 1


if __name__ == "__main__":
    unittest.main()
