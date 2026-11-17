"""Alembic environment: metadata tu app.models, URL tu settings."""
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings
from app.core.database import Base
import app.models.user  # noqa: F401
import app.models.profile  # noqa: F401
import app.models.cv  # noqa: F401
import app.models.job  # noqa: F401
import app.models.skill  # noqa: F401
import app.models.skill_gap  # noqa: F401
import app.models.audit_log  # noqa: F401

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
