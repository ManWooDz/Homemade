from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from database.models import Notification, User, UserIngredient

BANGKOK = timezone(timedelta(hours=7))


def _iso(value):
    return value.replace(tzinfo=value.tzinfo or timezone.utc).isoformat() if value else None


def public_notification(row):
    return {"id": row.id, "kind": row.kind, "target_type": row.target_type,
            "target_id": row.target_id, "payload": row.payload,
            "created_at": _iso(row.created_at), "read_at": _iso(row.read_at)}


def unread_count(db, user_id):
    return db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id, Notification.withdrawn_at.is_(None), Notification.read_at.is_(None)))


def list_notifications(db, user_id, *, state="unread", limit=20, before_id=None):
    stmt = select(Notification).where(Notification.user_id == user_id, Notification.withdrawn_at.is_(None))
    stmt = stmt.where(Notification.read_at.is_(None) if state == "unread" else Notification.read_at.is_not(None))
    if before_id is not None:
        stmt = stmt.where(Notification.id < before_id)
    rows = db.scalars(stmt.order_by(Notification.id.desc()).limit(limit + 1)).all()
    return {"items": [public_notification(row) for row in rows[:limit]],
            "unread_count": unread_count(db, user_id),
            "next_before_id": rows[limit - 1].id if len(rows) > limit else None}


def mark_read(db, user_id, notification_id):
    row = db.scalar(select(Notification).where(Notification.id == notification_id,
        Notification.user_id == user_id, Notification.withdrawn_at.is_(None)))
    if row is None:
        return None
    db.execute(update(Notification).where(Notification.id == row.id, Notification.read_at.is_(None))
               .values(read_at=datetime.now(timezone.utc)))
    db.commit()
    db.refresh(row)
    return public_notification(row)


def mark_all_read(db, user_id):
    db.execute(update(Notification).where(Notification.user_id == user_id,
        Notification.withdrawn_at.is_(None), Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc)))
    db.commit()
    return {"unread_count": unread_count(db, user_id)}


def lock_notification_owner(db, user_id):
    # Serialize foreground reconciliation with fridge edits for the same account.
    db.scalar(select(User.id).where(User.id == user_id).with_for_update())


def withdraw_ingredient_notifications(db, user_id, ingredient_id):
    db.execute(update(Notification).where(Notification.user_id == user_id,
        Notification.target_type == "ingredient", Notification.target_id == ingredient_id,
        Notification.withdrawn_at.is_(None)).values(withdrawn_at=datetime.now(timezone.utc)))


def record_save_notification(db, *, user_id, kind, target_type, target_id, name):
    event_key = f"history:{target_id}" if kind == "recipe_history_saved" else f"favorite:{target_type}:{uuid4().hex}"
    row = Notification(user_id=user_id, kind=kind, event_key=event_key,
        target_type=target_type, target_id=target_id, payload={"name": name[:500]},
        created_at=datetime.now(timezone.utc))
    db.add(row)
    db.flush()
    return row


def history_save_notification(db, user_id, history_id):
    row = db.scalar(select(Notification).where(Notification.user_id == user_id,
        Notification.event_key == f"history:{history_id}"))
    return public_notification(row) if row else None


def sync_expiry_notifications(db, user_id, *, now=None):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(BANGKOK).date()
    try:
        lock_notification_owner(db, user_id)
        ingredients = {row.id: row for row in db.scalars(select(UserIngredient)
            .where(UserIngredient.user_id == user_id).execution_options(populate_existing=True)).all()}
        reminders = db.scalars(select(Notification).where(Notification.user_id == user_id,
            Notification.target_type == "ingredient")).all()
        for reminder in reminders:
            source = ingredients.get(reminder.target_id)
            valid = source is not None and source.expiry_date is not None and reminder.payload.get("expiry_date") == source.expiry_date.isoformat()
            reminder.withdrawn_at = None if valid else (reminder.withdrawn_at or now)
        db.flush()
        dialect = db.get_bind().dialect.name
        if dialect not in ("postgresql", "sqlite"):
            raise RuntimeError("Unsupported notification database")
        insert = pg_insert if dialect == "postgresql" else sqlite_insert
        created_ids = []
        for ingredient in ingredients.values():
            if ingredient.expiry_date is None:
                continue
            days = (ingredient.expiry_date - today).days
            if days > 3:
                continue
            stage = "passed" if days < 0 else "today" if days == 0 else "near"
            stmt = insert(Notification).values(user_id=user_id, kind=f"expiry_{stage}",
                event_key=f"expiry:{ingredient.id}:{ingredient.expiry_date.isoformat()}:{stage}",
                target_type="ingredient", target_id=ingredient.id,
                payload={"name": ingredient.name[:500], "expiry_date": ingredient.expiry_date.isoformat()}, created_at=now)
            new_id = db.scalar(stmt.on_conflict_do_nothing(index_elements=["user_id", "event_key"]).returning(Notification.id))
            if new_id is not None:
                created_ids.append(new_id)
        db.commit()
        created = db.scalars(select(Notification).where(Notification.id.in_(created_ids)).order_by(Notification.id.desc())).all() if created_ids else []
        return {"created_items": [public_notification(row) for row in created], "unread_count": unread_count(db, user_id)}
    except Exception:
        db.rollback()
        raise
