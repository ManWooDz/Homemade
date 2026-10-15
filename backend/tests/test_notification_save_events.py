import unittest
from unittest.mock import patch

from sqlalchemy import func, select
from database.models import BaseRecipe, BaseRecipeFavorite, Favorite, GenerateHistory, Notification
from history_repository import insert_generate_history, set_favorite
from base_favorites_repository import set_base_favorite
from test_notification_repository import NotificationFixture


class NotificationSaveTests(NotificationFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.output = {"recipe_name": "Omelet", "instructions": ["Cook eggs"], "adjusted_ingredients": ["eggs"]}
        self.recipe = BaseRecipe(name="Omelet")
        self.db.add(self.recipe)
        self.db.commit()

    def test_history_save_and_notice_commit_together(self):
        history_id = insert_generate_history(self.db, user_id=self.user.id, request_recipe={}, final_output=self.output)
        notice = self.db.scalar(select(Notification))
        self.assertEqual((notice.kind, notice.target_id), ("recipe_history_saved", history_id))
        self.assertEqual(self.db.get(GenerateHistory, history_id).recipe_name, "Omelet")

    def test_history_notice_failure_rolls_back_primary_save(self):
        with patch("history_repository.record_save_notification", side_effect=RuntimeError("synthetic write failure")):
            with self.assertRaises(RuntimeError):
                insert_generate_history(self.db, user_id=self.user.id, request_recipe={}, final_output=self.output)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(GenerateHistory)), 0)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Notification)), 0)

    def test_base_favorite_noop_remove_readd(self):
        notices = []
        for action in (True, True, False, False, True):
            self.assertTrue(set_base_favorite(self.db, user_id=self.user.id, base_recipe_id=self.recipe.id, favorite=action, notifications=notices))
        self.assertEqual(len(notices), 2)
        self.assertEqual(len({notice["id"] for notice in notices}), 2)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Notification)), 2)

    def test_generated_favorite_noop_remove_readd(self):
        history_id = insert_generate_history(self.db, user_id=self.user.id, request_recipe={}, final_output=self.output)
        notices = []
        for action in (True, True, False, True):
            self.assertTrue(set_favorite(self.db, user_id=self.user.id, history_id=history_id, favorite=action, notifications=notices))
        self.assertEqual(len(notices), 2)
        self.assertEqual(notices[0]["target_type"], "history")
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Notification)), 3)

    def test_favorite_notice_failure_rolls_back_both_sources(self):
        history_id = insert_generate_history(self.db, user_id=self.user.id, request_recipe={}, final_output=self.output)
        for repo, function, arguments, table in (
            ("base_favorites_repository", set_base_favorite, {"base_recipe_id": self.recipe.id}, BaseRecipeFavorite),
            ("history_repository", set_favorite, {"history_id": history_id}, Favorite),
        ):
            with patch(f"{repo}.record_save_notification", side_effect=RuntimeError("synthetic failure")):
                with self.assertRaises(RuntimeError):
                    function(self.db, user_id=self.user.id, favorite=True, **arguments)
            self.assertEqual(self.db.scalar(select(func.count()).select_from(table)), 0)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Notification)), 1)

    def test_other_owner_cannot_favorite_generated_history(self):
        history_id = insert_generate_history(self.db, user_id=self.user.id, request_recipe={}, final_output=self.output)
        self.assertFalse(set_favorite(self.db, user_id=self.other.id, history_id=history_id, favorite=True))
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Notification)), 1)

    def test_commit_failure_after_both_writes_rolls_back_without_announcing(self):
        notices = []
        with patch.object(self.db, "commit", side_effect=RuntimeError("synthetic commit failure")):
            with self.assertRaises(RuntimeError):
                set_base_favorite(self.db, user_id=self.user.id, base_recipe_id=self.recipe.id, favorite=True, notifications=notices)
        self.assertEqual(notices, [])
        self.assertEqual(self.db.scalar(select(func.count()).select_from(BaseRecipeFavorite)), 0)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Notification)), 0)


if __name__ == "__main__":
    unittest.main()
