"""Read database DDL and write a reviewable SQL snapshot; never changes DB."""
from pathlib import Path
import os

BACKEND_DIR = Path(__file__).resolve().parent
os.chdir(BACKEND_DIR)

from app.core.config import settings
from app.core.database import Base, engine
from app.models import cv, job, profile, skill, skill_gap, user
from sqlalchemy import inspect


def main():
    output_dir = BACKEND_DIR.parent / "docs" / "database"
    output_dir.mkdir(parents=True, exist_ok=True)
    inspector = inspect(engine)
    names = inspector.get_table_names()
    ordered = [table.name for table in Base.metadata.sorted_tables if table.name in names]
    ordered += sorted(set(names) - set(ordered))
    database_name = settings.DB_NAME.replace("`", "``")
    parts = [
        "-- SQL snapshot of the current MySQL database, 2026-10-10.",
        "-- Structure only: no account data, CV content or credentials.",
        "-- Review reference; this file does not migrate existing tables.",
        "SET NAMES utf8mb4;",
        f"USE `{database_name}`;",
    ]
    with engine.connect() as connection:
        for name in ordered:
            safe_name = name.replace("`", "``")
            row = connection.exec_driver_sql(f"SHOW CREATE TABLE `{safe_name}`").first()
            parts.extend([f"-- Table: {name}", row[1] + ";"])
    target = output_dir / "schema_current.sql"
    target.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"EXPORTED: {target}")
    print(f"TABLES ({len(ordered)}): " + ", ".join(ordered))
    for model_table in Base.metadata.sorted_tables:
        if model_table.name not in names:
            print(f"MISSING TABLE: {model_table.name}")
            continue
        actual = {column["name"]: column for column in inspector.get_columns(model_table.name)}
        missing = set(model_table.columns.keys()) - set(actual)
        if missing:
            print(f"MISSING COLUMNS {model_table.name}: " + ", ".join(sorted(missing)))
    print("ACTUAL ROLE: " + str(next(c["type"] for c in inspector.get_columns("users") if c["name"] == "role")))
    print("ROLE VALUES: " + repr(next(c["type"] for c in inspector.get_columns("users") if c["name"] == "role").enums))
    print("SKILL GAP UNIQUE: " + repr(inspector.get_unique_constraints("skill_gaps")))


if __name__ == "__main__":
    main()
