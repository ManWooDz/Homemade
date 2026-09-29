import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
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


if __name__ == "__main__":
    unittest.main()
