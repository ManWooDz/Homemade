"""Add account language, display name and private normalized avatar.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
"""
from alembic import op
import sqlalchemy as sa

revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("display_name", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("locale", sa.String(2), nullable=False, server_default="th"))
    op.add_column("users", sa.Column("avatar_bytes", sa.LargeBinary(), nullable=True))
    op.create_check_constraint("ck_users_locale", "users", "locale IN ('th', 'en')")
    op.create_check_constraint("ck_users_avatar_size", "users", "avatar_bytes IS NULL OR length(avatar_bytes) <= 262144")


def downgrade():
    # Profile data must be exported/reviewed before a destructive rollback.
    raise RuntimeError("Profile downgrade would discard account data; use a reviewed recovery plan")
