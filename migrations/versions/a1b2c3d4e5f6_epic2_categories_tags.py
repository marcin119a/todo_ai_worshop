"""Epic 2: categories and tags

Revision ID: a1b2c3d4e5f6
Revises: 13c8aec48ae9
Create Date: 2026-03-28 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '13c8aec48ae9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Create category table (idempotent)
    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS category (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL UNIQUE,
            color VARCHAR(20)
        )
    """))
    bind.execute(text("CREATE INDEX IF NOT EXISTS ix_category_name ON category (name)"))

    # Add new columns to task (check first — SQLite < 3.37 has no IF NOT EXISTS for ADD COLUMN)
    existing = {row[1] for row in bind.execute(text("PRAGMA table_info(task)"))}

    if "category_id" not in existing:
        bind.execute(text("ALTER TABLE task ADD COLUMN category_id INTEGER REFERENCES category(id)"))
        bind.execute(text("CREATE INDEX IF NOT EXISTS ix_task_category_id ON task (category_id)"))

    if "tags" not in existing:
        bind.execute(text("ALTER TABLE task ADD COLUMN tags JSON"))

    if "ai_override" not in existing:
        bind.execute(text("ALTER TABLE task ADD COLUMN ai_override BOOLEAN NOT NULL DEFAULT 0"))


def downgrade() -> None:
    # SQLite does not support DROP COLUMN before 3.35; use batch mode to rebuild table
    with op.batch_alter_table("task") as batch_op:
        batch_op.drop_column("ai_override")
        batch_op.drop_column("tags")
        batch_op.drop_column("category_id")

    op.drop_index("ix_category_name", table_name="category")
    op.drop_table("category")
