"""Add case_template_id to Case model

Revision ID: bf5eab0b7ace
Revises: d5a720d1b99b
Create Date: 2025-05-15 03:28:27.999462

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import String
from app.alembic.alembic_utils import _table_has_column

# revision identifiers, used by Alembic.
revision = 'bf5eab0b7ace'
down_revision = 'd5a720d1b99b'
branch_labels = None
depends_on = None


def upgrade():
    # Check if the column doesn't exist before adding it
    if not _table_has_column('cases', 'case_template_id'):
        op.add_column('cases', sa.Column('case_template_id', String(length=256), nullable=True))


def downgrade():
    pass
