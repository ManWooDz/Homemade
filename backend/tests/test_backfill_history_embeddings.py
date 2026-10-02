"""Offline backfill contracts exercised without a provider or live database."""
import importlib
import importlib.util
import io
import os
import unittest
from unittest.mock import patch

from sqlalchemy import null, select, update
from sqlalchemy.orm import sessionmaker

from database.models import GenerateHistory, Rating
from test_history_repository import make_session, make_user


VECTOR = [1.0] + [0.0] * 767
WINNER = [0.0, 1.0] + [0.0] * 766


class FakeTime:
    def __init__(self):
        self.now = 0.0
        self.waits = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


class BackfillTests(unittest.TestCase):
    def setUp(self):
        self.db = make_session()
        self.owner = make_user(self.db, "backfill-owner@example.com").id
        self.other = make_user(self.db, "backfill-other@example.com").id
        self.factory = sessionmaker(bind=self.db.get_bind(), autoflush=False)
        self.output = io.StringIO()
        self.time = FakeTime()
        self.calls = []
        enabled = patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "1"})
        enabled.start()
        self.addCleanup(enabled.stop)
        self.addCleanup(self.db.close)

    def module(self):
        self.assertIsNotNone(
            importlib.util.find_spec("database.backfill_history_embeddings"),
            "explicit history embedding backfill command is missing",
        )
        return importlib.import_module("database.backfill_history_embeddings")

    def add_history(self, history_id, stars=5, *, owner=None, rating_owner=None,
                    embedding=None):
        user_id = self.owner if owner is None else owner
        self.db.add(GenerateHistory(
            id=history_id, user_id=user_id, source="generated",
            recipe_name=f"Recipe {history_id}",
            adjusted_ingredients=["หมูสับ 200 กรัม", "น้ำมัน 1 ช้อนโต๊ะ"],
            diet_tags=["Thai"], embedding=embedding,
            recipe_data={"private": "private recipe payload"},
        ))
        if stars is not None:
            self.db.add(Rating(
                user_id=user_id if rating_owner is None else rating_owner,
                generate_history_id=history_id, stars=stars,
                feedback="private feedback", tag="Tasty",
            ))
        self.db.commit()
        if embedding is None:
            # Model VECTOR NULL, not SQLite's test-only JSON null encoding.
            self.db.execute(update(GenerateHistory).where(
                GenerateHistory.id == history_id
            ).values(embedding=null()))
            self.db.commit()

    def embed(self, documents):
        self.calls.append((self.time.clock(), list(documents)))
        return [list(VECTOR) for _ in documents]

    def run_backfill(self, **overrides):
        arguments = dict(
            session_factory=self.factory, embedder=self.embed,
            clock=self.time.clock, sleep=self.time.sleep, stdout=self.output,
        )
        arguments.update(overrides)
        return self.module().run_backfill(**arguments)

    def stored(self, history_id):
        with self.factory() as reader:
            return reader.get(GenerateHistory, history_id).embedding

    def test_selects_only_signal_ratings_with_matching_history_owner_and_null_vector(self):
        # Dropping any join/filter would fill one of ids 3, 6, 7, or 8.
        for stars in (1, 2, 3, 4, 5):
            self.add_history(stars, stars)
        self.add_history(6, None)
        self.add_history(7, rating_owner=self.other)
        self.add_history(8, embedding=WINNER)
        self.add_history(9, owner=self.other, stars=2)
        self.assertEqual(self.run_backfill(), 0)
        for history_id in (1, 2, 4, 5, 9):
            self.assertEqual(self.stored(history_id), VECTOR)
        for history_id in (3, 6, 7):
            self.assertIsNone(self.stored(history_id))
        self.assertEqual(self.stored(8), WINNER)
        self.assertEqual(sum(len(docs) for _, docs in self.calls), 5)

    def test_embeds_reused_document_builder_fields_in_deterministic_history_id_order(self):
        # Losing ORDER BY id or embedding raw recipe_data breaks these literals.
        for history_id in (90, 10, 70):
            self.add_history(history_id)
        self.assertEqual(self.run_backfill(batch_size=2), 0)
        self.assertEqual([docs for _, docs in self.calls], [
            ["Recipe 10 | วัตถุดิบ: หมูสับ, น้ำมัน | diet_tags: Thai",
             "Recipe 70 | วัตถุดิบ: หมูสับ, น้ำมัน | diet_tags: Thai"],
            ["Recipe 90 | วัตถุดิบ: หมูสับ, น้ำมัน | diet_tags: Thai"],
        ])

    def test_rerun_after_success_performs_zero_embedding_or_write_commits(self):
        self.add_history(1)
        self.assertEqual(self.run_backfill(), 0)
        with patch.object(self.db, "commit", wraps=self.db.commit) as commit:
            self.assertEqual(self.run_backfill(session_factory=lambda: self.db), 0)
            self.assertEqual(commit.call_count, 0)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.stored(1), VECTOR)

    def test_neutral_rating_becomes_eligible_after_changing_to_signal(self):
        self.add_history(1, 3)
        self.assertEqual(self.run_backfill(), 0)
        self.assertEqual(self.calls, [])
        self.db.execute(update(Rating).values(stars=4))
        self.db.commit()
        self.assertEqual(self.run_backfill(), 0)
        self.assertEqual(self.stored(1), VECTOR)
        self.assertEqual(len(self.calls), 1)

    def test_concurrent_vector_winner_is_preserved_while_other_batch_rows_are_written(self):
        # Replacing the conditional UPDATE with ORM assignment loses WINNER.
        self.add_history(1)
        self.add_history(2)

        def embed(documents):
            with self.factory() as writer:
                writer.execute(update(GenerateHistory).where(
                    GenerateHistory.id == 1
                ).values(embedding=WINNER))
                writer.commit()
            return self.embed(documents)

        self.assertEqual(self.run_backfill(embedder=embed), 0)
        self.assertEqual(self.stored(1), WINNER)
        self.assertEqual(self.stored(2), VECTOR)
        self.assertIn("written=1", self.output.getvalue())
        self.assertIn("skipped=1", self.output.getvalue())

    def test_owner_change_during_embedding_prevents_stale_owner_write(self):
        # Removing the write-time owner predicate leaks across ownership changes.
        self.add_history(1)

        def embed(documents):
            with self.factory() as writer:
                writer.execute(update(GenerateHistory).values(user_id=self.other))
                writer.commit()
            return self.embed(documents)

        self.assertEqual(self.run_backfill(embedder=embed), 0)
        self.assertIsNone(self.stored(1))

    def test_rating_that_becomes_neutral_during_embedding_is_not_written(self):
        self.add_history(1)

        def embed(documents):
            with self.factory() as writer:
                writer.execute(update(Rating).values(stars=3))
                writer.commit()
            return self.embed(documents)

        self.assertEqual(self.run_backfill(embedder=embed), 0)
        self.assertIsNone(self.stored(1))

    def test_default_rate_budget_counts_80_inputs_not_outer_api_calls(self):
        # Call-based quota or a default above 80 sends input 81 before t=60.
        for history_id in range(1, 82):
            self.add_history(history_id)
        self.assertEqual(self.run_backfill(batch_size=40), 0)
        self.assertEqual([(at, len(docs)) for at, docs in self.calls],
                         [(0.0, 40), (0.0, 40), (60.0, 1)])
        self.assertEqual(self.time.waits, [60.0])

    def test_batch_size_and_budget_are_both_measured_by_embedded_input_count(self):
        # A batch larger than the configured per-minute input limit must split.
        for history_id in range(1, 8):
            self.add_history(history_id)
        self.assertEqual(self.run_backfill(batch_size=5, inputs_per_minute=3), 0)
        self.assertEqual([(at, len(docs)) for at, docs in self.calls],
                         [(0.0, 3), (60.0, 3), (120.0, 1)])

    def test_rate_window_uses_injected_clock_including_time_spent_embedding(self):
        for history_id in range(1, 4):
            self.add_history(history_id)

        def embed(documents):
            vectors = self.embed(documents)
            self.time.now += 10.0
            return vectors

        self.assertEqual(self.run_backfill(
            batch_size=2, inputs_per_minute=2, embedder=embed,
        ), 0)
        self.assertEqual([at for at, _ in self.calls], [0.0, 60.0])
        self.assertEqual(self.time.waits, [50.0])

    def test_one_commit_per_db_batch_and_no_transaction_during_provider_or_sleep(self):
        for history_id in range(1, 6):
            self.add_history(history_id)
        self.db.close()

        def embed(documents):
            self.assertFalse(self.db.in_transaction())
            return self.embed(documents)

        def sleep(seconds):
            self.assertFalse(self.db.in_transaction())
            self.time.sleep(seconds)

        with patch.object(self.db, "commit", wraps=self.db.commit) as commit:
            self.assertEqual(self.run_backfill(
                batch_size=2, inputs_per_minute=2,
                session_factory=lambda: self.db, embedder=embed, sleep=sleep,
            ), 0)
            self.assertEqual(commit.call_count, 3)
        self.assertEqual([self.stored(i) for i in range(1, 6)], [VECTOR] * 5)

    def test_failed_commit_rolls_back_whole_batch_preserving_previous_commits_and_retry(self):
        # Per-row commits or swallowing a commit error leaves partial writes.
        for history_id in range(1, 6):
            self.add_history(history_id)
        self.db.close()
        real_commit = self.db.commit
        commits = []

        def commit():
            commits.append(1)
            if len(commits) == 2:
                raise RuntimeError("private recipe feedback secret-key [0.12345]")
            real_commit()

        with patch.object(self.db, "commit", side_effect=commit), \
                patch.object(self.db, "rollback", wraps=self.db.rollback) as rollback:
            self.assertEqual(self.run_backfill(
                batch_size=2, session_factory=lambda: self.db,
            ), 1)
            self.assertEqual(rollback.call_count, 1)
        self.assertEqual([self.stored(i) for i in (1, 2)], [VECTOR, VECTOR])
        self.assertEqual([self.stored(i) for i in (3, 4, 5)], [None, None, None])
        self.calls.clear()
        self.assertEqual(self.run_backfill(batch_size=2), 0)
        self.assertEqual([len(docs) for _, docs in self.calls], [2, 1])
        self.assertEqual([self.stored(i) for i in range(1, 6)], [VECTOR] * 5)
        self.assertNotIn("secret-key", self.output.getvalue())

    def test_mid_batch_update_failure_rolls_back_earlier_updates_in_same_batch(self):
        self.add_history(1)
        self.add_history(2)
        self.db.close()
        real_execute = self.db.execute
        updates = []

        def execute(statement, *args, **kwargs):
            if statement.is_update:
                updates.append(1)
                if len(updates) == 2:
                    raise RuntimeError("private update payload")
            return real_execute(statement, *args, **kwargs)

        with patch.object(self.db, "execute", side_effect=execute):
            self.assertEqual(self.run_backfill(session_factory=lambda: self.db), 1)
        self.assertEqual(self.stored(1), None)
        self.assertEqual(self.stored(2), None)

    def test_api_failure_returns_nonzero_leaves_null_vectors_and_does_not_print_secrets(self):
        self.add_history(1)

        def fail(documents):
            raise RuntimeError("Recipe 1 private feedback secret-key " + documents[0])

        self.assertEqual(self.run_backfill(embedder=fail), 1)
        self.assertIsNone(self.stored(1))
        self.assertIn("failed", self.output.getvalue().lower())
        for secret in ("Recipe 1", "private feedback", "secret-key", "วัตถุดิบ"):
            self.assertNotIn(secret, self.output.getvalue())

    def test_short_api_response_does_not_silently_commit_partial_embeddings(self):
        self.add_history(1)
        self.add_history(2)
        self.assertEqual(self.run_backfill(embedder=lambda documents: [VECTOR]), 1)
        self.assertEqual([self.stored(i) for i in (1, 2)], [None, None])

    def test_db_selection_failure_returns_nonzero_without_embedding(self):
        self.add_history(1)
        with patch.object(self.db, "execute", side_effect=RuntimeError("private SQL")):
            self.assertEqual(self.run_backfill(session_factory=lambda: self.db), 1)
        self.assertEqual(self.calls, [])
        self.assertNotIn("private SQL", self.output.getvalue())

    def test_success_output_contains_counts_and_ids_but_no_private_content_or_vectors(self):
        self.add_history(17)
        self.assertEqual(self.run_backfill(), 0)
        output = self.output.getvalue()
        self.assertIn("17", output)
        self.assertIn("written=1", output)
        for secret in ("Recipe 17", "private", "feedback", "หมูสับ", "Thai", "1.0", "0.0"):
            self.assertNotIn(secret, output)

    def test_disabled_run_exits_zero_before_database_or_embedding_access(self):
        def forbidden(*args, **kwargs):
            raise AssertionError("disabled backfill accessed dependency")

        with patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "0"}):
            self.assertEqual(self.run_backfill(
                session_factory=forbidden, embedder=forbidden,
            ), 0)
        self.assertIn("disabled", self.output.getvalue().lower())

    def test_invalid_rate_or_batch_limits_fail_before_database_access(self):
        for options in ({"batch_size": 0}, {"inputs_per_minute": 0},
                        {"batch_size": -1}, {"inputs_per_minute": -1}):
            with self.subTest(options=options):
                self.assertEqual(self.run_backfill(
                    session_factory=lambda: self.fail("invalid config opened DB"), **options,
                ), 2)

    def test_cli_refuses_writes_without_literal_preflight_acknowledgement(self):
        self.add_history(1)
        status = self.module().main(
            [], session_factory=lambda: self.fail("unconfirmed CLI opened DB"),
            embedder=lambda documents: self.fail("unconfirmed CLI embedded"),
            stdout=self.output,
        )
        self.assertNotEqual(status, 0)
        self.assertIsNone(self.stored(1))
        self.assertIn("--confirm-preflight-passed", self.output.getvalue())

    def test_disabled_cli_exits_zero_even_without_acknowledgement_or_db_configuration(self):
        with patch.dict(os.environ, {"PERSONALIZATION_ENABLED": "0"}), \
                patch("database.db.SessionLocal", side_effect=AssertionError("DB opened")), \
                patch("embeddings.embed_history_documents", side_effect=AssertionError("API called")):
            self.assertEqual(self.module().main([], stdout=self.output), 0)
        self.assertIn("disabled", self.output.getvalue().lower())

    def test_cli_rejects_abbreviated_preflight_flag_before_writes(self):
        # argparse's default prefix matching must not weaken literal acknowledgement.
        with patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit) as exit_status:
            self.module().main(
                ["--confirm-preflight"], stdout=self.output,
                session_factory=lambda: self.fail("abbreviated flag opened DB"),
                embedder=lambda documents: self.fail("abbreviated flag embedded"),
            )
        self.assertEqual(exit_status.exception.code, 2)

    def test_confirmed_cli_api_failure_is_nonzero(self):
        self.add_history(1)

        def fail(documents):
            raise RuntimeError("secret-key Recipe 1")

        status = self.module().main(
            ["--confirm-preflight-passed", "--batch-size", "1", "--inputs-per-minute", "80"],
            session_factory=self.factory, embedder=fail, stdout=self.output,
            clock=self.time.clock, sleep=self.time.sleep,
        )
        self.assertEqual(status, 1)
        self.assertIsNone(self.stored(1))
        self.assertNotIn("secret-key", self.output.getvalue())

    def test_confirmed_cli_uses_existing_session_configuration_and_batch_embedder(self):
        self.add_history(1)
        with patch("database.db.SessionLocal", self.factory), \
                patch("embeddings.embed_history_documents", side_effect=self.embed):
            self.assertEqual(self.module().main(
                ["--confirm-preflight-passed"], stdout=self.output,
                clock=self.time.clock, sleep=self.time.sleep,
            ), 0)
        self.assertEqual(self.stored(1), VECTOR)
        self.assertEqual(self.calls[0][1],
                         ["Recipe 1 | วัตถุดิบ: หมูสับ, น้ำมัน | diet_tags: Thai"])

    def test_import_never_creates_session_or_runs_embedding(self):
        # Module-level execution would reach either patched external boundary.
        module = self.module()
        with patch("database.db.SessionLocal", side_effect=AssertionError("import opened DB")), \
                patch("embeddings.embed_history_documents", side_effect=AssertionError("import embedded")):
            importlib.reload(module)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
