"""
Sprint 8 — Alembic migration tests.

Tests:
1. alembic.ini exists and is readable
2. alembic/env.py exists and imports Base metadata
3. alembic/script.py.mako exists
4. alembic/versions/ directory exists
5. Initial migration file exists
6. alembic upgrade head works against a local SQLite test DB
"""

import os
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths (relative to apps/api/)
# ---------------------------------------------------------------------------

API_DIR = Path(__file__).resolve().parent.parent   # apps/api/
ALEMBIC_INI = API_DIR / "alembic.ini"
ALEMBIC_ENV = API_DIR / "alembic" / "env.py"
ALEMBIC_MAKO = API_DIR / "alembic" / "script.py.mako"
ALEMBIC_VERSIONS = API_DIR / "alembic" / "versions"


# ---------------------------------------------------------------------------
# File existence checks
# ---------------------------------------------------------------------------

def test_alembic_ini_exists():
    assert ALEMBIC_INI.exists(), "alembic.ini not found in apps/api/"


def test_alembic_env_exists():
    assert ALEMBIC_ENV.exists(), "alembic/env.py not found in apps/api/alembic/"


def test_alembic_mako_exists():
    assert ALEMBIC_MAKO.exists(), "alembic/script.py.mako not found"


def test_alembic_versions_dir_exists():
    assert ALEMBIC_VERSIONS.is_dir(), "alembic/versions/ directory not found"


def test_initial_migration_exists():
    migrations = list(ALEMBIC_VERSIONS.glob("*.py"))
    assert len(migrations) >= 1, (
        "No migration files found in alembic/versions/. "
        "Expected at least 0001_initial_schema.py"
    )


def test_initial_migration_has_upgrade_and_downgrade():
    migrations = list(ALEMBIC_VERSIONS.glob("*.py"))
    assert migrations, "No migration files found"
    first = sorted(migrations)[0].read_text()
    assert "def upgrade()" in first, "Initial migration missing upgrade() function"
    assert "def downgrade()" in first, "Initial migration missing downgrade() function"


# ---------------------------------------------------------------------------
# Content checks
# ---------------------------------------------------------------------------

def test_alembic_env_imports_base_metadata():
    env_text = ALEMBIC_ENV.read_text()
    assert "Base" in env_text, "env.py must import/use the SQLAlchemy Base"
    assert "target_metadata" in env_text, "env.py must set target_metadata"


def test_alembic_env_imports_models():
    env_text = ALEMBIC_ENV.read_text()
    # Must import models to populate Base.metadata
    assert "app.db.models" in env_text or "app.db.base" in env_text, (
        "env.py must import app.db.models or app.db.base to populate metadata"
    )


def test_alembic_ini_has_script_location():
    ini_text = ALEMBIC_INI.read_text()
    assert "script_location" in ini_text, "alembic.ini must specify script_location"
    assert "alembic" in ini_text, "alembic.ini script_location should point to alembic/"


# ---------------------------------------------------------------------------
# Functional check: alembic upgrade head against SQLite
# ---------------------------------------------------------------------------

def test_alembic_upgrade_head_sqlite():
    """Run alembic upgrade head against a temp SQLite DB."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite:///{db_path}",
        }
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(API_DIR),
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"alembic upgrade head failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
    finally:
        try:
            os.unlink(db_path)
        except FileNotFoundError:
            pass
