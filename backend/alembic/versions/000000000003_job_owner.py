"""Them jobs.owner_id de phan quyen recruiter theo so huu.

Revision ID: 000000000003
Jobs cu (owner NULL) van thuoc quyen admin; recruiter chi thay job do ho tao.
"""

revision = "000000000003"
down_revision = "000000000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        cols = {c["name"] for c in insp.get_columns("jobs")}
    except Exception:
        cols = set()
    if "owner_id" not in cols:
        op.add_column("jobs", sa.Column("owner_id", sa.Integer(), nullable=True))
        try:
            op.create_index("ix_jobs_owner_id", "jobs", ["owner_id"])
        except Exception:
            pass
        try:
            op.create_foreign_key(
                "fk_jobs_owner_id_users", "jobs", "users",
                ["owner_id"], ["id"], ondelete="SET NULL",
            )
        except Exception:
            pass


def downgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        cols = {c["name"] for c in insp.get_columns("jobs")}
    except Exception:
        cols = set()
    if "owner_id" in cols:
        try:
            op.drop_constraint("fk_jobs_owner_id_users", "jobs", type_="foreignkey")
        except Exception:
            pass
        try:
            op.drop_index("ix_jobs_owner_id", table_name="jobs")
        except Exception:
            pass
        op.drop_column("jobs", "owner_id")
