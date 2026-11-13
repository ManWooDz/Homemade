from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import UserIngredient
from image_urls import public_image_url
from notification_repository import lock_notification_owner, withdraw_ingredient_notifications

_BARCODE_BINDING_KEY = "_barcode_product"


def barcode_binding(row: UserIngredient):
    return (row.nutrition_data or {}).get(_BARCODE_BINDING_KEY)


def _display_nutrition(row: UserIngredient):
    return {key: value for key, value in (row.nutrition_data or {}).items()
            if key != _BARCODE_BINDING_KEY} or None


def _with_barcode_binding(nutrition_data, binding, *, active=True):
    return {
        **(nutrition_data or {}),
        _BARCODE_BINDING_KEY: {**binding, "active": active, "revision": uuid4().hex},
    }


def _public_ingredient(row: UserIngredient):
    result = {
        "id": row.id,
        "name": row.name,
        "category": row.category,
        "image": public_image_url(row.image),
        "selected": True,
        "expiry_date": row.expiry_date.isoformat() if row.expiry_date else None,
        "nutrition_data": _display_nutrition(row),
        "quantity_amount": row.quantity_amount,
        "quantity_unit": row.quantity_unit,
    }
    if binding := barcode_binding(row):
        result["barcode_product"] = {
            "barcode": binding["barcode"],
            "name": binding["product_name"],
            "revision": binding["revision"],
            "active": binding["active"],
        }
    return result


def load_owned_fridge_items(db: Session, user_id: int, ingredient_ids):
    if not ingredient_ids:
        return {}
    rows = db.scalars(select(UserIngredient).where(
        UserIngredient.user_id == user_id, UserIngredient.id.in_(ingredient_ids)
    ))
    return {row.id: row for row in rows}


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
    db: Session,
    *,
    user_id: int,
    name,
    category,
    image,
    expiry_date=None,
    nutrition_data=None,
    barcode_binding=None,
    quantity_amount=None,
    quantity_unit=None,
):
    row = UserIngredient(
        user_id=user_id,
        name=name,
        category=category,
        quantity=None,
        image=image,
        expiry_date=expiry_date,
        nutrition_data=_with_barcode_binding(nutrition_data, barcode_binding) if barcode_binding else nutrition_data,
        quantity_amount=quantity_amount,
        quantity_unit=quantity_unit,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _public_ingredient(row)


def delete_user_ingredient(db: Session, *, user_id: int, ingredient_id: int):
    lock_notification_owner(db, user_id)
    row = db.execute(
        select(UserIngredient).where(
            UserIngredient.id == ingredient_id, UserIngredient.user_id == user_id
        )
    ).scalar_one_or_none()
    if row is None:
        return False
    withdraw_ingredient_notifications(db, user_id, ingredient_id)
    db.delete(row)
    db.commit()
    return True


def update_user_ingredient(db: Session, *, user_id: int, ingredient_id: int, values: dict | None,
                           new_binding=None, barcode_nutrition_data=None):
    lock_notification_owner(db, user_id)
    row = load_owned_fridge_items(db, user_id, [ingredient_id]).get(ingredient_id)
    if row is None:
        return None
    if values is not None and row.expiry_date != values["expiry_date"]:
        withdraw_ingredient_notifications(db, user_id, ingredient_id)
    old_binding = barcode_binding(row)
    if new_binding:
        display = barcode_nutrition_data
        if display is None and old_binding and old_binding["barcode"] == new_binding["barcode"]:
            display = _display_nutrition(row)
        row.nutrition_data = _with_barcode_binding(display, new_binding)
    elif old_binding and values is not None and row.name != values["name"]:
        row.nutrition_data = _with_barcode_binding(_display_nutrition(row), old_binding, active=False)
    if values is not None:
        for field in ("name", "category", "expiry_date", "quantity_amount", "quantity_unit"):
            setattr(row, field, values[field])
    db.commit()
    db.refresh(row)
    return _public_ingredient(row)
