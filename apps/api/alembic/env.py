"""
Alembic env.py for DemandOS.

Uses the SQLAlchemy metadata from app.db.base to drive autogenerate migrations.
Falls back to DATABASE_URL environment variable; defaults to the dev SQLite DB.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import the Base and all models so Alembic can see the metadata.
from app.db.base import Base
import app.db.models  # noqa: F401 — side-effect import populates Base.metadata

# ---------------------------------------------------------------------------
# Alembic config object (reads alembic.ini)
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging (if present).
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use our SQLAlchemy metadata for autogenerate support.
target_metadata = Base.metadata

# Override sqlalchemy.url from environment if provided.
_db_url = os.environ.get("DATABASE_URL", "sqlite:///./demandos_dev.db")
config.set_main_option("sqlalchemy.url", _db_url)


# ---------------------------------------------------------------------------
# Offline migration (generates SQL without connecting to DB)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration (connects to DB and runs migrations)
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
