"""Gop role employer thanh recruiter.

Revision ID: 000000000002
Chuyen du lieu hien co role='employer' sang 'recruiter', sau do thu hep ENUM
ve ('user', 'admin', 'recruiter'). SQLite khong co ENUM that nen chi can
update du lieu; MySQL can them ALTER MODIFY.
"""
from alembic import op
import sqlalchemy as sa

revision = "000000000002"
down_revision = "000000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("UPDATE users SET role = 'recruiter' WHERE role = 'employer'")
    if bind.dialect.name == "mysql":
        op.execute(
            "ALTER TABLE users MODIFY COLUMN role "
            "ENUM('user', 'admin', 'recruiter') NOT NULL DEFAULT 'user'"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute(
            "ALTER TABLE users MODIFY COLUMN role "
            "ENUM('user', 'admin', 'employer', 'recruiter') NOT NULL DEFAULT 'user'"
        )
    op.execute("UPDATE users SET role = 'employer' WHERE role = 'recruiter'")
