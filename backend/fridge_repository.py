from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import UserIngredient


def _public_ingredient(row: UserIngredient):
    return {
        "id": row.id,
        "name": row.name,
        "category": row.category,
        "image": row.image,
        "selected": True,
        "expiry_date": row.expiry_date.isoformat() if row.expiry_date else None,
        "nutrition_data": row.nutrition_data,
    }


def list_user_ingredients(db: Session, user_id: int):
    rows = db.execute(
        select(UserIngredient)
        .where(UserIngredient.user_id == user_id)
        # Nearest-expiry first so every consumer of this list (fridge view,
        # recipe ingredient pickers) gets the same "use it soon" ordering
        # for free. Every pre-existing row has a NULL expiry_date, and
        # NULLS LAST doesn't order ties among those NULLs — id.asc() keeps
        # that group stable across reloads.
        .order_by(UserIngredient.expiry_date.asc().nulls_last(), UserIngredient.id.asc())
    ).scalars().all()
    return [_public_ingredient(row) for row in rows]


def insert_user_ingredient(
    db: Session, *, user_id: int, name, category, image, expiry_date=None, nutrition_data=None
):
    row = UserIngredient(
        user_id=user_id,
        name=name,
        category=category,
        quantity=None,
        image=image,
        expiry_date=expiry_date,
        nutrition_data=nutrition_data,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _public_ingredient(row)


def delete_user_ingredient(db: Session, *, user_id: int, ingredient_id: int):
    row = db.execute(
        select(UserIngredient).where(
            UserIngredient.id == ingredient_id, UserIngredient.user_id == user_id
        )
    ).scalar_one_or_none()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
