"""Baseline tong hop: thay the cac script run_migration_002..008 roi rac.

Revision ID: 000000000001
Thay the toan bo ALTER TABLE roi (soft delete, file_hash, role,
analysis_run_id, job_snapshot/matched_at, cv_input_hash, token_version)
bang mot revision duy nhat co the chay lai (kiem tra cot truoc khi them).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME as MySQLDateTime

revision = "000000000001"
down_revision = None
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        cols = {c["name"] for c in insp.get_columns(table)}
    except Exception:
        return False
    return column in cols


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if not _has_column(table, column.name):
        op.add_column(table, column)


def upgrade() -> None:
    # DB trang (docker lan dau): tao toan bo bang tu metadata truoc khi ALTER.
    # DB cu da co bang: create_all(checkfirst) la no-op, an toan.
    from app.core.database import Base
    import app.models.user  # noqa: F401
    import app.models.profile  # noqa: F401
    import app.models.cv  # noqa: F401
    import app.models.job  # noqa: F401
    import app.models.skill  # noqa: F401
    import app.models.skill_gap  # noqa: F401
    import app.models.audit_log  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind)
    # users.token_version (thu hoi JWT)
    _add_column_if_missing("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    # jobs / skills soft delete
    for table in ("jobs", "skills"):
        _add_column_if_missing(table, sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="0"))
        _add_column_if_missing(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    # cvs.file_hash + analysis_run_id
    _add_column_if_missing("cvs", sa.Column("file_hash", sa.String(64), nullable=True))
    _add_column_if_missing("cvs", sa.Column("analysis_run_id", sa.String(32), nullable=True))
    # skill_gaps snapshot/hash/matched_at
    _add_column_if_missing("skill_gaps", sa.Column("job_snapshot", sa.JSON(), nullable=True))
    _add_column_if_missing("skill_gaps", sa.Column("cv_input_hash", sa.String(64), nullable=True))
    _add_column_if_missing(
        "skill_gaps",
        sa.Column("matched_at", sa.DateTime(timezone=True).with_variant(MySQLDateTime(fsp=6), "mysql"), nullable=True),
    )
    # role ENUM: mo rong de chua ca gia tri cu (employer) va moi (recruiter);
    # revision 000000000002 se chuyen du lieu va thu hep lai.
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        try:
            op.execute(
                "ALTER TABLE users MODIFY COLUMN role "
                "ENUM('user', 'admin', 'employer', 'recruiter') NOT NULL DEFAULT 'user'"
            )
        except Exception:
            pass


def downgrade() -> None:
    # Chi go cac cot do revision nay them; khong xoa cot goc cua schema.
    for table, col in (
        ("users", "token_version"),
        ("jobs", "is_deleted"), ("jobs", "deleted_at"),
        ("skills", "is_deleted"), ("skills", "deleted_at"),
        ("cvs", "file_hash"), ("cvs", "analysis_run_id"),
        ("skill_gaps", "job_snapshot"), ("skill_gaps", "cv_input_hash"), ("skill_gaps", "matched_at"),
    ):
        if _has_column(table, col):
            op.drop_column(table, col)
