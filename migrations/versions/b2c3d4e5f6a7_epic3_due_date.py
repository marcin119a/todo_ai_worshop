"""Epic 3: due_date field for tasks

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-28 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {row[1] for row in bind.execute(text("PRAGMA table_info(task)"))}

    if "due_date" not in existing:
        bind.execute(text("ALTER TABLE task ADD COLUMN due_date DATE"))


def downgrade() -> None:
    with op.batch_alter_table("task") as batch_op:
        batch_op.drop_column("due_date")
