"""Account-owned in-app notifications; no historical-save backfill."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("event_key", sa.String(200), nullable=False),
        sa.Column("target_type", sa.String(16), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "event_key", name="uq_notifications_event"),
        sa.CheckConstraint("kind IN ('expiry_near','expiry_today','expiry_passed','recipe_history_saved','recipe_favorite_added')", name="ck_notifications_kind"),
        sa.CheckConstraint("target_type IN ('ingredient','history','base_recipe') AND target_id > 0", name="ck_notifications_target"),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_notifications_feed", "notifications", ["user_id", "withdrawn_at", "read_at", "id"])


def downgrade():
    raise RuntimeError("Notification downgrade discards history; use separately reviewed recovery")
