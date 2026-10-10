"""Check migration configuration without connecting to PostgreSQL."""
import runpy
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from alembic import context

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def migration_env(tmp_path, monkeypatch):
    env_path = tmp_path / "backend/alembic/env.py"
    env_path.parent.mkdir(parents=True)
    env_path.write_text((ROOT / "backend/alembic/env.py").read_text())
    config = MagicMock(config_file_name=None)
    monkeypatch.setattr(context, "config", config, raising=False)
    monkeypatch.setattr(context, "is_offline_mode", lambda: True)
    for name in ("configure", "begin_transaction", "run_migrations"):
        monkeypatch.setattr(context, name, MagicMock())
    monkeypatch.delenv("DATABASE_URL", raising=False)
    return env_path, config


@pytest.mark.parametrize("source", ["root", "backend", "environment"])
def test_database_configuration_precedence(migration_env, tmp_path, monkeypatch, source):
    env_path, config = migration_env
    (tmp_path / ".env").write_text("DATABASE_URL=postgresql+asyncpg://localhost/root_test\n")
    if source != "root":
        (tmp_path / "backend/.env").write_text(
            "DATABASE_URL=postgresql+asyncpg://localhost/backend_test\n"
        )
    if source == "environment":
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/environment_test")
    runpy.run_path(str(env_path))
    config.set_main_option.assert_called_once_with(
        "sqlalchemy.url", f"postgresql+psycopg2://localhost/{source}_test"
    )


def test_migrations_require_explicit_database_credentials(migration_env):
    env_path, _ = migration_env
    with pytest.raises(RuntimeError, match="Set DATABASE_URL"):
        runpy.run_path(str(env_path))
