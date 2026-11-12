from sqlalchemy import text

from app.db.models import Base
from app.db.session import engine


def _ensure_manager_queue_email_columns() -> None:
    """Add nullable email columns on existing Postgres/SQLite deployments."""
    statements = (
        "ALTER TABLE manager_queue ADD COLUMN IF NOT EXISTS email_message_id VARCHAR(512)",
        "ALTER TABLE manager_queue ADD COLUMN IF NOT EXISTS email_subject VARCHAR(998)",
    )
    dialect = engine.dialect.name
    with engine.begin() as connection:
        if dialect == "sqlite":
            existing = {
                row[1]
                for row in connection.execute(text("PRAGMA table_info(manager_queue)")).fetchall()
            }
            if "email_message_id" not in existing:
                connection.execute(
                    text("ALTER TABLE manager_queue ADD COLUMN email_message_id VARCHAR(512)")
                )
            if "email_subject" not in existing:
                connection.execute(
                    text("ALTER TABLE manager_queue ADD COLUMN email_subject VARCHAR(998)")
                )
            return
        for statement in statements:
            connection.execute(text(statement))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    try:
        _ensure_manager_queue_email_columns()
    except Exception:
        # Fresh create_all already has columns; ignore alter races.
        pass
