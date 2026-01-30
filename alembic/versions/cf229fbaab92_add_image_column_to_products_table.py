"""add image column to products table

Revision ID: cf229fbaab92
Revises: 002_add_client_id
Create Date: 2026-01-29 21:51:03.258962

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf229fbaab92'
down_revision: Union[str, Sequence[str], None] = '002_add_client_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('products', sa.Column('image', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('products', 'image')
