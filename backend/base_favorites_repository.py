from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.models import BaseRecipe, BaseRecipeFavorite


def list_base_favorite_ids(db: Session, user_id: int) -> list[int]:
    stmt = (
        select(BaseRecipeFavorite.base_recipe_id)
        .where(BaseRecipeFavorite.user_id == user_id)
        .order_by(BaseRecipeFavorite.id.asc())
    )
    return list(db.execute(stmt).scalars().all())


def set_base_favorite(db: Session, *, user_id: int, base_recipe_id: int, favorite: bool) -> bool:
    """Returns False only when favoriting a base recipe that does not exist."""
    if not favorite:
        # Single atomic DELETE (mirrors history_repository.set_favorite): racing
        # double-DELETEs both succeed. No recipe-existence check on removal.
        db.execute(
            delete(BaseRecipeFavorite).where(
                BaseRecipeFavorite.user_id == user_id,
                BaseRecipeFavorite.base_recipe_id == base_recipe_id,
            )
        )
        db.commit()
        return True
    if db.get(BaseRecipe, base_recipe_id) is None:
        return False
    existing = db.execute(
        select(BaseRecipeFavorite).where(
            BaseRecipeFavorite.user_id == user_id,
            BaseRecipeFavorite.base_recipe_id == base_recipe_id,
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(BaseRecipeFavorite(user_id=user_id, base_recipe_id=base_recipe_id))
        try:
            db.commit()
        except IntegrityError:
            # Concurrent insert of the same (user, recipe) pair: already present.
            db.rollback()
    return True
