"""Credential configuration checks that never connect to a database or provider."""
import importlib.util
import secrets
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import bcrypt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def load_migration():
    path = ROOT / "backend/alembic/versions/001_initial_schema.py"
    spec = importlib.util.spec_from_file_location("credential_migration", path)
    module = importlib.util.module_from_spec(spec)
    # Mock migration operations before import; no Alembic engine is needed.
    with patch("alembic.op", MagicMock()):
        spec.loader.exec_module(module)
    return module


def inserted_users(migration):
    return [
        call.args[0] for call in migration.op.execute.call_args_list
        if "INSERT INTO users" in str(call.args[0])
    ]


def test_migration_does_not_seed_a_default_password(monkeypatch):
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    migration = load_migration()
    migration.upgrade()
    assert inserted_users(migration) == []


def test_migration_hashes_only_the_environment_password(monkeypatch):
    password = "Aa1!" + secrets.token_urlsafe(24)
    monkeypatch.setenv("DEMO_PASSWORD", password)
    migration = load_migration()
    migration.upgrade()
    statements = inserted_users(migration)
    assert len(statements) == 1
    values = statements[0].compile().params
    assert values["pwd"] != password
    assert bcrypt.checkpw(password.encode(), values["pwd"].encode())


def test_application_has_no_demo_password_fallback(monkeypatch):
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    from app.config import Settings

    settings = Settings(
        _env_file=None,
        jwt_secret_key=secrets.token_urlsafe(48),
        database_url="postgresql+asyncpg://localhost/geordiedaz_test",
    )
    assert settings.demo_password == ""


def test_application_reads_password_from_environment_file(tmp_path, monkeypatch):
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    from app.config import Settings

    password = "Aa1!" + secrets.token_urlsafe(24)
    env_file = tmp_path / ".env"
    env_file.write_text(f"DEMO_PASSWORD={password}\n")
    settings = Settings(
        _env_file=env_file,
        jwt_secret_key=secrets.token_urlsafe(48),
        database_url="postgresql+asyncpg://localhost/geordiedaz_test",
    )
    assert settings.demo_password == password
