import os
import sys
import threading
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import null, select, update

import main
from database.models import GenerateHistory, Rating
from history_repository import insert_generate_history, upsert_rating
from test_history_repository import APPROVED, make_session, make_user


VECTOR = [1.0] + [0.0] * 767
DOCUMENT = "Thai Basil Pork | วัตถุดิบ: หมูสับ, น้ำมัน | diet_tags: Thai"


class RatingEmbeddingBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = make_session()
        self.user_id = make_user(self.db, "embedding-owner@example.com").id
        self.history_id = insert_generate_history(
            self.db, user_id=self.user_id, request_recipe={}, final_output=deepcopy(APPROVED)
        )
        # Model the target PostgreSQL VECTOR column's SQL NULL, rather than
        # SQLite's test-only JSON representation of Python None.
        self.db.execute(update(GenerateHistory).values(embedding=null()))
        self.db.commit()
        self.db.close()
        enabled = patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "1"})
        enabled.start()
        self.addCleanup(enabled.stop)
        self.addCleanup(self.db.close)

    def commit_rating(self, stars):
        return upsert_rating(
            self.db, user_id=self.user_id, history_id=self.history_id,
            stars=stars, tag="Tasty", feedback="private feedback",
        )

    async def embed(self, saved):
        boundary = getattr(main, "embed_rated_history_best_effort", None)
        self.assertTrue(callable(boundary), "post-commit embedding boundary is missing")
        return await boundary(
            self.db, user_id=self.user_id, history_id=self.history_id, rating=saved
        )

    def stored_vector(self):
        return self.db.get(GenerateHistory, self.history_id).embedding

    async def test_neutral_stars_skip_snapshot_and_embedding(self):
        saved = self.commit_rating(3)
        with patch("main.get_history_embedding_snapshot", create=True, side_effect=AssertionError("snapshot must skip")) as snapshot, \
                patch("main.embed_history_documents", create=True, side_effect=AssertionError("embedding must skip")) as embedder:
            self.assertIsNone(await self.embed(saved))
        snapshot.assert_not_called()
        embedder.assert_not_called()
        self.assertIsNone(self.stored_vector())

    async def test_disabled_flag_skips_snapshot_and_embedding_for_signal(self):
        saved = self.commit_rating(5)
        with patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "0"}), \
                patch("main.get_history_embedding_snapshot", create=True, side_effect=AssertionError("snapshot must skip")) as snapshot, \
                patch("main.embed_history_documents", create=True, side_effect=AssertionError("embedding must skip")) as embedder:
            self.assertIsNone(await self.embed(saved))
        snapshot.assert_not_called()
        embedder.assert_not_called()
        self.assertIsNone(self.stored_vector())

    async def test_signal_stars_store_embedding_after_close_in_threadpool(self):
        request_thread = threading.get_ident()
        for stars in (1, 2, 4, 5):
            with self.subTest(stars=stars):
                self.db.execute(update(GenerateHistory).values(embedding=null()))
                self.db.commit()
                saved = self.commit_rating(stars)
                self.assertTrue(self.db.in_transaction(), "rating refresh opens a transaction")
                observations = []

                def embedder(documents):
                    self.assertEqual(documents, [DOCUMENT])
                    self.assertFalse(self.db.in_transaction())
                    self.assertGreaterEqual(close.call_count, 1)
                    observations.append(threading.get_ident())
                    return [VECTOR]

                with patch.object(self.db, "close", wraps=self.db.close) as close, \
                        patch("main.embed_history_documents", create=True, side_effect=embedder), \
                        patch("main.run_in_threadpool", wraps=main.run_in_threadpool) as threadpool:
                    await self.embed(saved)
                self.assertEqual(len(observations), 1)
                self.assertNotEqual(observations[0], request_thread)
                self.assertEqual(threadpool.await_count, 1)
                self.assertFalse(self.db.in_transaction())
                self.assertEqual(self.stored_vector(), VECTOR)

    async def test_existing_vector_skips_remote_embedding(self):
        self.db.get(GenerateHistory, self.history_id).embedding = VECTOR
        self.db.commit()
        saved = self.commit_rating(2)
        with patch("main.embed_history_documents", create=True, side_effect=AssertionError("must not re-embed")) as embedder:
            await self.embed(saved)
        embedder.assert_not_called()
        self.assertEqual(self.stored_vector(), VECTOR)

    async def test_api_failure_leaves_committed_rating_and_safe_log(self):
        saved = self.commit_rating(5)
        with patch("main.embed_history_documents", create=True, side_effect=RuntimeError("secret-key private recipe prompt vector feedback")), \
                self.assertLogs("personalization", level="WARNING") as logs:
            self.assertIsNone(await self.embed(saved))
        self.assertIsNone(self.stored_vector())
        rating = self.db.execute(select(Rating)).scalar_one()
        self.assertEqual((rating.stars, rating.tag, rating.feedback), (5, "Tasty", "private feedback"))
        message = "\n".join(logs.output)
        self.assertIn("stage=history_embedding", message)
        self.assertIn("error=RuntimeError", message)
        self.assertIn(f"user_id={self.user_id}", message)
        self.assertIn(f"history_id={self.history_id}", message)
        for secret in ("secret-key", "private recipe", "prompt", "vector", "feedback", "Thai Basil Pork"):
            self.assertNotIn(secret, message)

    async def test_snapshot_failure_closes_refresh_transaction_without_remote_work(self):
        saved = self.commit_rating(4)
        with patch("main.get_history_embedding_snapshot", create=True, side_effect=RuntimeError("private snapshot")), \
                patch("main.embed_history_documents", create=True, side_effect=AssertionError("must skip remote work")), \
                self.assertLogs("personalization", level="WARNING"):
            self.assertIsNone(await self.embed(saved))
        self.assertFalse(self.db.in_transaction())
        rating = self.db.execute(select(Rating)).scalar_one()
        self.assertEqual(rating.stars, 4)

    async def test_close_failure_skips_remote_work_and_preserves_rating(self):
        saved = self.commit_rating(4)
        with patch.object(self.db, "close", side_effect=RuntimeError("private close")), \
                patch("main.embed_history_documents", create=True, side_effect=AssertionError("must skip remote work")), \
                self.assertLogs("personalization", level="WARNING"):
            self.assertIsNone(await self.embed(saved))
        self.assertFalse(self.db.in_transaction())
        rating = self.db.execute(select(Rating)).scalar_one()
        self.assertEqual(rating.stars, 4)


class RatingEmbeddingEndpointTests(unittest.IsolatedAsyncioTestCase):
    setUp = RatingEmbeddingBoundaryTests.setUp
    stored_vector = RatingEmbeddingBoundaryTests.stored_vector

    async def rate(self, *, stars=5, tag="Great", feedback="committed feedback"):
        return await main.put_history_rating(
            self.history_id, main.RatingRequest(stars=stars, tag=tag, feedback=feedback),
            current_user=SimpleNamespace(id=self.user_id), db=self.db,
        )

    async def test_handler_embeds_only_after_rating_is_committed_and_refreshed(self):
        observations = []

        def embedder(documents):
            self.assertFalse(self.db.in_transaction())
            self.assertEqual(documents, [DOCUMENT])
            # A separate session must already observe the authoritative rating.
            from sqlalchemy.orm import sessionmaker
            with sessionmaker(bind=self.db.get_bind())() as reader:
                rating = reader.execute(select(Rating)).scalar_one()
                observations.append((rating.stars, rating.tag, rating.feedback))
            return [VECTOR]

        with patch("main.embed_history_documents", side_effect=embedder):
            response = await self.rate()
        self.assertEqual(response, {
            "status": "success", "data": {"stars": 5, "tag": "Great", "feedback": "committed feedback"}
        })
        self.assertEqual(observations, [(5, "Great", "committed feedback")])
        self.assertEqual(self.stored_vector(), VECTOR)

    async def test_api_failure_still_returns_committed_rating_success(self):
        with patch("main.embed_history_documents", side_effect=RuntimeError("private API failure")), \
                self.assertLogs("personalization", level="WARNING") as logs:
            response = await self.rate()
        self.assertEqual(response, {
            "status": "success", "data": {"stars": 5, "tag": "Great", "feedback": "committed feedback"}
        })
        self.assertIn("stage=history_embedding", "\n".join(logs.output))
        self.assertIsNone(self.stored_vector())
        rating = self.db.execute(select(Rating)).scalar_one()
        self.assertEqual((rating.stars, rating.tag, rating.feedback), (5, "Great", "committed feedback"))

    async def test_vector_commit_failure_still_returns_committed_rating_success(self):
        real_commit = self.db.commit
        commits = []

        def fail_vector_commit():
            commits.append("commit")
            if len(commits) == 2:
                raise RuntimeError("private vector failure")
            return real_commit()

        with patch("main.embed_history_documents", return_value=[VECTOR]), \
                patch.object(self.db, "commit", side_effect=fail_vector_commit), \
                self.assertLogs("personalization", level="WARNING") as logs:
            response = await self.rate()
        self.assertEqual(response, {
            "status": "success", "data": {"stars": 5, "tag": "Great", "feedback": "committed feedback"}
        })
        self.assertEqual(len(commits), 2)
        self.assertIn("stage=history_embedding_update", "\n".join(logs.output))
        self.assertNotIn("private vector failure", "\n".join(logs.output))
        self.assertIsNone(self.stored_vector())
        rating = self.db.execute(select(Rating)).scalar_one()
        self.assertEqual((rating.stars, rating.tag, rating.feedback), (5, "Great", "committed feedback"))

    async def test_tag_feedback_only_rerating_preserves_vector_without_embedding(self):
        with patch("main.embed_history_documents", return_value=[VECTOR]):
            await self.rate()
        self.assertEqual(self.stored_vector(), VECTOR)
        with patch("main.embed_history_documents", side_effect=AssertionError("must not re-embed")) as embedder:
            response = await self.rate(tag="Tasty", feedback="updated feedback")
        embedder.assert_not_called()
        self.assertEqual(response, {
            "status": "success", "data": {"stars": 5, "tag": "Tasty", "feedback": "updated feedback"}
        })
        self.assertEqual(self.stored_vector(), VECTOR)
        rating = self.db.execute(select(Rating)).scalar_one()
        self.assertEqual((rating.stars, rating.tag, rating.feedback), (5, "Tasty", "updated feedback"))


if __name__ == "__main__":
    unittest.main()
