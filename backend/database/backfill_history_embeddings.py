"""Explicit offline history embedding backfill; never runs on import.

Run from backend with:
    python -m database.backfill_history_embeddings --confirm-preflight-passed

Only an operator who has checked the preflight should acknowledge it. Rate
accounting counts embedded inputs, including inputs in failed API attempts.
"""
import argparse
from collections import deque
import os
import sys
import time


def _disabled(stdout):
    if os.getenv("PERSONALIZATION_ENABLED", "1") == "0":
        print("History embedding backfill disabled", file=stdout)
        return True
    return False


def _select_batch(session_factory, after_id, limit):
    from sqlalchemy import and_, select

    from database.models import GenerateHistory, Rating
    from history_repository import HistoryEmbeddingSnapshot

    db = session_factory()
    try:
        rows = db.execute(
            select(
                GenerateHistory.id, GenerateHistory.user_id,
                GenerateHistory.recipe_name, GenerateHistory.adjusted_ingredients,
                GenerateHistory.diet_tags,
            )
            .join(Rating, and_(
                Rating.generate_history_id == GenerateHistory.id,
                Rating.user_id == GenerateHistory.user_id,
            ))
            .where(
                GenerateHistory.id > after_id,
                GenerateHistory.embedding.is_(None),
                Rating.stars.in_((1, 2, 4, 5)),
            )
            .order_by(GenerateHistory.id)
            .limit(limit)
        ).all()
        return [HistoryEmbeddingSnapshot(
            history_id=row.id, user_id=row.user_id,
            recipe_name=row.recipe_name,
            adjusted_ingredients=tuple(row.adjusted_ingredients or ()),
            diet_tags=tuple(row.diet_tags or ()), embedding=None,
        ) for row in rows]
    finally:
        # Release the read transaction before provider work or rate waits.
        db.close()


def _write_batch(session_factory, snapshots, vectors):
    from sqlalchemy import exists, update

    from database.models import GenerateHistory, Rating

    db = session_factory()
    try:
        written = 0
        for snapshot, vector in zip(snapshots, vectors, strict=True):
            result = db.execute(
                update(GenerateHistory)
                .where(
                    GenerateHistory.id == snapshot.history_id,
                    GenerateHistory.user_id == snapshot.user_id,
                    GenerateHistory.embedding.is_(None),
                    exists().where(
                        Rating.generate_history_id == GenerateHistory.id,
                        Rating.user_id == GenerateHistory.user_id,
                        Rating.stars.in_((1, 2, 4, 5)),
                    ),
                )
                .values(embedding=vector)
                .execution_options(synchronize_session=False)
            )
            written += result.rowcount
        db.commit()
        return written
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run_backfill(
    *, session_factory=None, embedder=None, batch_size=20,
    inputs_per_minute=80, clock=time.monotonic, sleep=time.sleep, stdout=None,
) -> int:
    """Return an exit status; injected dependencies enable entirely offline runs.

    Each invocation scans eligible ids once. Concurrent losers remain eligible
    for a later invocation; committed vectors are never replaced. The rolling
    60-second budget is local to this process, so run only one backfill at a time.
    """
    output = stdout if stdout is not None else sys.stdout
    if _disabled(output):
        return 0
    if batch_size < 1 or inputs_per_minute < 1:
        print("Invalid backfill batch or rate limit", file=output)
        return 2

    embedded = written = skipped = 0
    after_id = 0
    reservations = deque()
    stage = "configuration"
    try:
        if session_factory is None:
            from database.db import SessionLocal
            if SessionLocal is None:
                raise RuntimeError("Database is not configured")
            session_factory = SessionLocal

        # Keep the builder and normalization exclusively in Task 1's helpers.
        from embeddings import build_history_document, embed_history_documents
        if embedder is None:
            embedder = embed_history_documents

        while True:
            stage = "selection"
            snapshots = _select_batch(
                session_factory, after_id, min(batch_size, inputs_per_minute),
            )
            if not snapshots:
                break
            documents = [build_history_document(
                row.recipe_name, row.adjusted_ingredients, row.diet_tags,
            ) for row in snapshots]

            stage = "rate_wait"
            while True:
                now = clock()
                while reservations and now - reservations[0][0] >= 60:
                    reservations.popleft()
                if sum(count for _, count in reservations) + len(documents) <= inputs_per_minute:
                    break
                sleep(max(0.0, 60 - (now - reservations[0][0])))
            reservations.append((clock(), len(documents)))

            stage = "embedding"
            embedded += len(documents)
            vectors = embedder(documents)
            if len(vectors) != len(snapshots):
                raise RuntimeError("Embedding count mismatch")

            stage = "write"
            batch_written = _write_batch(session_factory, snapshots, vectors)
            written += batch_written
            skipped += len(snapshots) - batch_written
            after_id = snapshots[-1].history_id
            print(
                f"Batch ids={[row.history_id for row in snapshots]} "
                f"embedded={len(documents)} written={batch_written} "
                f"skipped={len(snapshots) - batch_written}", file=output,
            )
    except Exception:
        # SQL/provider exceptions may include keys, payloads, and bind values.
        print(
            f"Backfill failed stage={stage} embedded={embedded} "
            f"written={written} skipped={skipped}", file=output,
        )
        return 1
    print(
        f"Backfill complete embedded={embedded} written={written} skipped={skipped}",
        file=output,
    )
    return 0


def main(argv=None, *, stdout=None, **dependencies) -> int:
    """Require the literal operator acknowledgement before entering the writer."""
    from dotenv import load_dotenv

    load_dotenv()
    output = stdout if stdout is not None else sys.stdout
    if _disabled(output):
        return 0
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--confirm-preflight-passed", action="store_true")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--inputs-per-minute", type=int, default=80)
    arguments = parser.parse_args(argv)
    if not arguments.confirm_preflight_passed:
        print("Refusing backfill: pass --confirm-preflight-passed", file=output)
        return 2
    return run_backfill(
        stdout=output, batch_size=arguments.batch_size,
        inputs_per_minute=arguments.inputs_per_minute, **dependencies,
    )


if __name__ == "__main__":
    raise SystemExit(main())
