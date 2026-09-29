"""personalization data capture: generate_history.recipe_data, ratings.tag/feedback/updated_at

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'generate_history',
        sa.Column('recipe_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'"), nullable=False),
    )
    op.add_column('ratings', sa.Column('tag', sa.String(), nullable=True))
    op.add_column('ratings', sa.Column('feedback', sa.Text(), nullable=True))
    op.add_column(
        'ratings',
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ratings', 'updated_at')
    op.drop_column('ratings', 'feedback')
    op.drop_column('ratings', 'tag')
    op.drop_column('generate_history', 'recipe_data')
