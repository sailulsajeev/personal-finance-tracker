# src/services/db.py
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

# Import your models' Base so create_all() works,
# and Transaction for utility helpers (optional but convenient).
from src.models.transaction import Base, Transaction  # noqa: F401

# -----------------------
# Configuration
# -----------------------
DB_PATH = os.getenv("DB_PATH", "data/app.db")

# Ensure parent folder exists (e.g., "data/")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# SQLite engine
ENGINE: Engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},  # needed for Streamlit / threaded contexts
    future=True,
)

# Enable foreign keys on SQLite
@event.listens_for(ENGINE, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    try:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        # Best-effort; safe to ignore if unsupported
        pass

# Session factory
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)


# -----------------------
# Public API
# -----------------------
def init_db() -> None:
    """
    Create all tables defined on Base metadata (no-op if already created).
    Call this once on app startup.
    """
    Base.metadata.create_all(bind=ENGINE)


def get_session() -> Session:
    """
    Return a new Session. Remember to close() it after use,
    or prefer the session_scope() context manager below.
    """
    return SessionLocal()


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Context manager for a transactional scope:

        with session_scope() as session:
            # use session
            session.add(...)
            ...

    Commits on success; rolls back on exception; always closes.
    """
    session: Session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def clear_transactions() -> None:
    """
    Delete all rows from the 'transactions' table but keep schema intact.
    Useful for development/testing to quickly wipe data.
    """
    with session_scope() as session:
        # Use a raw SQL DELETE for speed (works fine for SQLite)
        session.execute(text("DELETE FROM transactions"))


def vacuum() -> None:
    """
    Reclaim space in SQLite database file (optional maintenance).
    """
    with session_scope() as session:
        session.execute(text("VACUUM"))


def reset_database(drop_file: bool = False) -> None:
    """
    Factory reset for your DB.
    - If drop_file=True, deletes the SQLite file and recreates fresh schema.
    - Else, truncates all tables via metadata and recreates (safer in some envs).

    Note: Dropping the file is simplest for local dev; avoid in production.
    """
    if drop_file:
        # Close all connections by disposing the engine first
        ENGINE.dispose()
        try:
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
        finally:
            # Recreate the folder if needed and rebuild schema
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            Base.metadata.create_all(bind=ENGINE)
        return

    # Non-destructive reset (drop & recreate tables via metadata)
    # Order matters with FKs; drop_all handles correct ordering.
    Base.metadata.drop_all(bind=ENGINE)
    Base.metadata.create_all(bind=ENGINE)


def get_engine() -> Engine:
    """Expose the SQLAlchemy Engine if you need low-level access."""
    return ENGINE
