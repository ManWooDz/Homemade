from dataclasses import dataclass

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from database.models import Favorite, GenerateHistory, Rating


@dataclass(frozen=True, slots=True)
class HistorySignal:
    history_id: int
    recipe_name: str
    adjusted_ingredients: tuple[str, ...]
    diet_tags: tuple[str, ...]
    stars: int
    rating_tag: str | None
    feedback: str | None
    is_favorite: bool


def _history_signal(
    history: GenerateHistory,
    rating: Rating,
    favorite_id: int | None,
) -> HistorySignal:
    return HistorySignal(
        history_id=history.id,
        recipe_name=history.recipe_name,
        adjusted_ingredients=tuple(history.adjusted_ingredients or ()),
        diet_tags=tuple(history.diet_tags or ()),
        stars=rating.stars,
        rating_tag=rating.tag,
        feedback=rating.feedback,
        is_favorite=favorite_id is not None,
    )


def _embedding_is_present(db: Session):
    condition = GenerateHistory.embedding.is_not(None)
    if db.get_bind().dialect.name == "sqlite":
        condition = and_(condition, func.json_type(GenerateHistory.embedding) != "null")
    return condition


def count_embedded_signals(db: Session, user_id: int) -> int:
    stmt = (
        select(func.count(GenerateHistory.id))
        .join(Rating, Rating.generate_history_id == GenerateHistory.id)
        .where(
            GenerateHistory.user_id == user_id,
            Rating.user_id == user_id,
            Rating.stars.in_((1, 2, 4, 5)),
            _embedding_is_present(db),
        )
    )
    return int(db.execute(stmt).scalar_one())


def retrieve_similar_signals(
    db: Session,
    user_id: int,
    query_embedding,
    stars,
    limit: int = 20,
) -> list[HistorySignal]:
    distance = GenerateHistory.embedding.cosine_distance(query_embedding)
    stmt = (
        select(GenerateHistory, Rating, Favorite.id)
        .join(Rating, Rating.generate_history_id == GenerateHistory.id)
        .outerjoin(
            Favorite,
            and_(
                Favorite.generate_history_id == GenerateHistory.id,
                Favorite.user_id == user_id,
            ),
        )
        .where(
            GenerateHistory.user_id == user_id,
            Rating.user_id == user_id,
            Rating.stars.in_(tuple(stars)),
            _embedding_is_present(db),
        )
        .order_by(distance, GenerateHistory.id)
        .limit(min(max(int(limit), 0), 20))
    )
    return [
        _history_signal(history, rating, favorite_id)
        for history, rating, favorite_id in db.execute(stmt).all()
    ]


def list_profile_signals(db: Session, user_id: int) -> list[HistorySignal]:
    stmt = (
        select(GenerateHistory, Rating, Favorite.id)
        .join(Rating, Rating.generate_history_id == GenerateHistory.id)
        .outerjoin(
            Favorite,
            and_(
                Favorite.generate_history_id == GenerateHistory.id,
                Favorite.user_id == user_id,
            ),
        )
        .where(
            GenerateHistory.user_id == user_id,
            Rating.user_id == user_id,
        )
        .order_by(GenerateHistory.id)
    )
    return [
        _history_signal(history, rating, favorite_id)
        for history, rating, favorite_id in db.execute(stmt).all()
    ]
