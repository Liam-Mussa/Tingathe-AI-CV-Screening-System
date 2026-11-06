"""Database engine and session management.

The production target is PostgreSQL (see schema.sql). For local development and
testing we allow a SQLite URL through DATABASE_URL, so the API can be exercised
without installing a database server. The SQLAlchemy models are identical in
both cases; only the DSN changes.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL

# SQLite needs check_same_thread=False because FastAPI serves requests from a
# thread pool. PostgreSQL does not use that argument.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yield a session and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they do not exist yet (used on first run)."""
    import models  # noqa: PLC0415 - imported here so models registers on Base

    Base.metadata.create_all(bind=engine)
