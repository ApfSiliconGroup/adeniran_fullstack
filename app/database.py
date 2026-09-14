"""Database engine, session dependency and a tiny SQLite migration helper."""

from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

connect_args: dict[str, object] = {}
if settings.is_sqlite:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# Columns added after the first release. SQLModel's `create_all` never
# alters an existing table, so an older clinic.db would keep crashing on
# every query. These statements bring such a file up to date in place.
_ADDED_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "users": [
        ("full_name", "VARCHAR NOT NULL DEFAULT ''"),
        ("is_active", "BOOLEAN NOT NULL DEFAULT 1"),
        ("created_at", "TIMESTAMP"),
    ],
    "doctors": [
        ("bio", "VARCHAR NOT NULL DEFAULT ''"),
        ("years_experience", "INTEGER NOT NULL DEFAULT 0"),
        ("consulting_room", "VARCHAR NOT NULL DEFAULT ''"),
        ("is_accepting", "BOOLEAN NOT NULL DEFAULT 1"),
    ],
    "appointments": [
        ("reason", "VARCHAR NOT NULL DEFAULT ''"),
        ("created_at", "TIMESTAMP"),
        ("updated_at", "TIMESTAMP"),
    ],
}


def run_lightweight_migrations() -> None:
    """Add any column that a previously created SQLite file is missing."""
    if not settings.is_sqlite:
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table, columns in _ADDED_COLUMNS.items():
            if table not in existing_tables:
                continue
            present = {
                column["name"] for column in inspector.get_columns(table)
            }
            for column_name, column_type in columns:
                if column_name in present:
                    continue
                connection.execute(
                    text(
                        f"ALTER TABLE {table} "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
                )


def create_db_and_tables() -> None:
    # Importing the models registers them on SQLModel.metadata.
    import app.models  # noqa: F401

    run_lightweight_migrations()
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
