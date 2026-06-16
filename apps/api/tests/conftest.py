"""
Shared pytest fixtures.

Key concern: SQLite in-memory databases are per-connection. We use StaticPool
so all connections in a test share the single in-memory connection (and its tables).

Strategy: monkeypatch app.db.session.engine and SessionLocal so ALL app code
(get_db, init_db, route handlers) uses the in-memory SQLite for a given test.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Register all ORM classes on Base.metadata exactly once during collection.
import app.db.models  # noqa: F401
from app.db.base import Base


@pytest.fixture
def override_db(monkeypatch):
    """
    Patch the session module so every DB call in the app uses a shared
    in-memory SQLite engine for the duration of one test.

    StaticPool ensures create_all() and all session connections use the same
    underlying SQLite connection, so tables created by create_all are visible
    to every session.
    """
    from app.db import session as db_session

    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    monkeypatch.setattr(db_session, "engine", test_engine)
    monkeypatch.setattr(db_session, "SessionLocal", TestSession)

    yield test_engine

    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def in_memory_db(override_db):
    """
    Provides a SQLAlchemy Session on the test engine.
    Use in ingestion / service-layer tests that hit the DB directly.
    """
    session = sessionmaker(bind=override_db)()
    try:
        yield session
    finally:
        session.close()
