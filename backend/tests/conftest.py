"""
GeordieDaz — Test Configuration & Fixtures
"""
import os
import secrets
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Override settings BEFORE importing the app
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"
os.environ["LLM_PROVIDER"] = "openai"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGSMITH_TRACING_V2"] = "false"
os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(48)
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL") or ""
os.environ["DATABASE_URL"] = TEST_DB_URL or "postgresql+asyncpg://localhost:5432/geordiedaz_test"
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL") or "redis://localhost:6379/1"
os.environ["ENVIRONMENT"] = "test"


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Use an explicit test database and roll back endpoint commits after each test."""
    if not TEST_DB_URL:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL test database")

    from app.database import Base
    from app.models import user, memory, session  # noqa: F401

    test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with test_engine.connect() as conn:
            transaction = await conn.begin()
            try:
                async with AsyncSession(
                    bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
                ) as db_session:
                    yield db_session
            finally:
                await transaction.rollback()
    finally:
        await test_engine.dispose()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    from app.database import get_db
    from app.main import app

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def test_user_data():
    """Standard test user credentials."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "Aa1!" + secrets.token_urlsafe(24),
    }
