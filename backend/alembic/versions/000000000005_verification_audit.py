"""Duyet recruiter (users.is_verified) + nhat ky kiem toan (audit_logs).

Revision ID: 000000000005
Tai khoan hien co nhan is_verified=true; recruiter dang ky moi cho admin duyet.
"""

revision = "000000000005"
down_revision = "000000000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        user_cols = {c["name"] for c in insp.get_columns("users")}
    except Exception:
        user_cols = set()
    if "is_verified" not in user_cols:
        op.add_column(
            "users",
            sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="1"),
        )
    try:
        tables = set(insp.get_table_names())
    except Exception:
        tables = set()
    if "audit_logs" not in tables:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("action", sa.String(64), nullable=False, index=True),
            sa.Column("target_type", sa.String(32), nullable=True),
            sa.Column("target_id", sa.Integer(), nullable=True),
            sa.Column("detail", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        tables = set(insp.get_table_names())
    except Exception:
        tables = set()
    if "audit_logs" in tables:
        op.drop_table("audit_logs")
    try:
        cols = {c["name"] for c in insp.get_columns("users")}
    except Exception:
        cols = set()
    if "is_verified" in cols:
        op.drop_column("users", "is_verified")
