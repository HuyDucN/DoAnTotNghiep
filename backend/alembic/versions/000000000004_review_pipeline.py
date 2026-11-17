"""Them pipeline so tuyen cho SkillGap: review_status, recruiter_note, reviewed_at.

Revision ID: 000000000004
Ban ghi cu nhan review_status='new', note/at giu NULL.
"""

revision = "000000000004"
down_revision = "000000000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        cols = {c["name"] for c in insp.get_columns("skill_gaps")}
    except Exception:
        cols = set()
    if "review_status" not in cols:
        status_type = (
            sa.Enum("new", "viewed", "shortlisted", "rejected", "hired", name="review_status")
            if bind.dialect.name == "mysql"
            else sa.String(16)
        )
        op.add_column(
            "skill_gaps",
            sa.Column("review_status", status_type, nullable=False, server_default="new"),
        )
    if "recruiter_note" not in cols:
        op.add_column("skill_gaps", sa.Column("recruiter_note", sa.Text(), nullable=True))
    if "reviewed_at" not in cols:
        op.add_column("skill_gaps", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    from alembic import op
    import sqlalchemy as sa

    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        cols = {c["name"] for c in insp.get_columns("skill_gaps")}
    except Exception:
        cols = set()
    for col in ("reviewed_at", "recruiter_note", "review_status"):
        if col in cols:
            op.drop_column("skill_gaps", col)
