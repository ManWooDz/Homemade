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
    }


def list_user_ingredients(db: Session, user_id: int):
    rows = db.execute(
        select(UserIngredient).where(UserIngredient.user_id == user_id)
    ).scalars().all()
    return [_public_ingredient(row) for row in rows]


def insert_user_ingredient(db: Session, *, user_id: int, name, category, image):
    row = UserIngredient(
        user_id=user_id,
        name=name,
        category=category,
        quantity=None,
        image=image,
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
