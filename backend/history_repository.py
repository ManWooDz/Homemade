from copy import deepcopy
from dataclasses import dataclass

from sqlalchemy import and_, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.models import BaseRecipe, Favorite, GenerateHistory, Rating
from image_urls import public_image_url


def _public_rating(rating: Rating):
    return {"stars": rating.stars, "tag": rating.tag, "feedback": rating.feedback}


def _public_history(history: GenerateHistory, rating, is_favorite: bool, base_image):
    return {
        "id": history.id,
        "recipe_name": history.recipe_name,
        "image": public_image_url(base_image),
        "diet_tags": list(history.diet_tags or []),
        "created_at": history.created_at.isoformat() if history.created_at else None,
        "rating": _public_rating(rating) if rating is not None else None,
        "is_favorite": is_favorite,
        "recipe_data": history.recipe_data or {},
    }


def _base_recipe_id(db: Session, request_recipe):
    raw = request_recipe.get("id") if isinstance(request_recipe, dict) else None
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    # Postgres binds ids as INTEGER; an out-of-range client-supplied id must not
    # reach db.get or the whole history insert fails (saved as NULL instead).
    if raw < 1 or raw > 2_147_483_647:
        return None
    return raw if db.get(BaseRecipe, raw) is not None else None


def insert_generate_history(db: Session, *, user_id: int, request_recipe, final_output: dict) -> int:
    row = GenerateHistory(
        user_id=user_id,
        source="generated",
        base_recipe_id=_base_recipe_id(db, request_recipe),
        recipe_name=final_output["recipe_name"],
        adjusted_ingredients=list(final_output.get("adjusted_ingredients") or []),
        diet_tags=list(final_output.get("diet_tags") or []),
        instructions=list(final_output.get("instructions") or []),
        nutrition=dict(final_output.get("nutrition") or {}),
        recipe_data=deepcopy(final_output),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.id


def list_history(db: Session, user_id: int):
    # UNIQUE(user_id, generate_history_id) on ratings and favorites keeps
    # these outer joins at one row per history entry.
    stmt = (
        select(GenerateHistory, Rating, Favorite.id, BaseRecipe.image)
        .outerjoin(Rating, and_(Rating.generate_history_id == GenerateHistory.id, Rating.user_id == user_id))
        .outerjoin(Favorite, and_(Favorite.generate_history_id == GenerateHistory.id, Favorite.user_id == user_id))
        .outerjoin(BaseRecipe, BaseRecipe.id == GenerateHistory.base_recipe_id)
        .where(GenerateHistory.user_id == user_id)
        .order_by(GenerateHistory.created_at.desc(), GenerateHistory.id.desc())
    )
    return [
        _public_history(history, rating, favorite_id is not None, base_image)
        for history, rating, favorite_id, base_image in db.execute(stmt).all()
    ]


def _owned_history(db: Session, user_id: int, history_id: int):
    return db.execute(
        select(GenerateHistory).where(GenerateHistory.id == history_id, GenerateHistory.user_id == user_id)
    ).scalar_one_or_none()


@dataclass(frozen=True)
class HistoryEmbeddingSnapshot:
    history_id: int
    user_id: int
    recipe_name: str
    adjusted_ingredients: tuple[str, ...]
    diet_tags: tuple[str, ...]
    embedding: tuple[float, ...] | None


def get_history_embedding_snapshot(db: Session, *, user_id: int, history_id: int):
    """Copy owned recipe fields so remote embedding needs no live ORM row."""
    row = _owned_history(db, user_id, history_id)
    if row is None:
        return None
    return HistoryEmbeddingSnapshot(
        history_id=row.id,
        user_id=row.user_id,
        recipe_name=row.recipe_name,
        adjusted_ingredients=tuple(row.adjusted_ingredients or ()),
        diet_tags=tuple(row.diet_tags or ()),
        embedding=tuple(row.embedding) if row.embedding is not None else None,
    )


def set_history_embedding_if_missing(db: Session, *, user_id: int, history_id: int, embedding) -> bool:
    """Atomically fill an owned NULL vector; an existing vector always wins."""
    try:
        result = db.execute(
            update(GenerateHistory)
            .where(
                GenerateHistory.id == history_id,
                GenerateHistory.user_id == user_id,
                GenerateHistory.embedding.is_(None),
            )
            .values(embedding=embedding)
        )
        if result.rowcount != 1:
            db.rollback()
            return False
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def upsert_rating(db: Session, *, user_id: int, history_id: int, stars: int, tag, feedback):
    if _owned_history(db, user_id, history_id) is None:
        return None
    # select-then-write works on SQLite and Postgres alike; a concurrent insert
    # of the same (user, history) pair surfaces as IntegrityError, retried once
    # as an update.
    for _ in range(2):
        rating = db.execute(
            select(Rating).where(Rating.user_id == user_id, Rating.generate_history_id == history_id)
        ).scalar_one_or_none()
        if rating is None:
            rating = Rating(user_id=user_id, generate_history_id=history_id, stars=stars, tag=tag, feedback=feedback)
            db.add(rating)
        else:
            rating.stars = stars
            rating.tag = tag
            rating.feedback = feedback
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(rating)
        return _public_rating(rating)
    raise RuntimeError("rating upsert conflicted twice")


def set_favorite(db: Session, *, user_id: int, history_id: int, favorite: bool) -> bool:
    if _owned_history(db, user_id, history_id) is None:
        return False
    if not favorite:
        # Single atomic DELETE: racing double-DELETEs both succeed (the second
        # matches zero rows) instead of load-then-delete raising StaleDataError.
        db.execute(
            delete(Favorite).where(Favorite.user_id == user_id, Favorite.generate_history_id == history_id)
        )
        db.commit()
        return True
    existing = db.execute(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.generate_history_id == history_id)
    ).scalar_one_or_none()
    if existing is None:
        db.add(Favorite(user_id=user_id, generate_history_id=history_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return True
