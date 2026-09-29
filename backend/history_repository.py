from copy import deepcopy

from sqlalchemy import and_, select
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
