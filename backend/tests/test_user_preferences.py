import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database.models import Base, User, UserPreference


class UserPreferenceModelTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[User.__table__, UserPreference.__table__])
        self.db = Session(self.engine)
        user = User(email="prefs@example.com")
        self.db.add(user)
        self.db.commit()
        self.user_id = user.id

    def tearDown(self):
        self.db.close()

    def test_insert_and_query_round_trip(self):
        row = UserPreference(
            user_id=self.user_id,
            age=25,
            cuisine_preferences=["อาหารไทย"],
            dietary_restrictions=["แพ้ถั่ว"],
            equipment=["กระทะ"],
            cooking_frequency="ทำเป็นประจำ — 5–6 ครั้ง/สัปดาห์",
            cooking_goals=["ประหยัดค่าอาหาร"],
        )
        self.db.add(row)
        self.db.commit()

        fetched = self.db.get(UserPreference, self.user_id)
        self.assertEqual(fetched.age, 25)
        self.assertEqual(fetched.cuisine_preferences, ["อาหารไทย"])
        self.assertEqual(fetched.dietary_restrictions, ["แพ้ถั่ว"])

    def test_user_id_is_the_primary_key(self):
        row = UserPreference(user_id=self.user_id)
        self.db.add(row)
        self.db.commit()
        # PK lookup by user_id must work directly — no separate surrogate id
        self.assertIsNotNone(self.db.get(UserPreference, self.user_id))


if __name__ == "__main__":
    unittest.main()
