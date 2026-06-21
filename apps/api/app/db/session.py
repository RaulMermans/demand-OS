import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_settings
from app.db.base import Base

logger = logging.getLogger(__name__)

settings = get_settings()

_db_url = settings.database_url

# In vercel mode, SQLite is not durable — each function invocation may use a fresh
# container. Log a warning; health check (/api/readiness) surfaces this as not_ready.
if settings.demandos_runtime_mode == "vercel" and _db_url.startswith("sqlite"):
    logger.warning(
        "DEMANDOS_RUNTIME_MODE=vercel but DATABASE_URL is SQLite. "
        "Install Neon from the Vercel Marketplace and set DATABASE_URL to a Postgres URL."
    )

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False} if _db_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
