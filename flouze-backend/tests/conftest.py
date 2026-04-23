"""
Test setup:
- PostgreSQL: requires a 'flouze_test' database.
  Create it once: docker compose exec db psql -U flouze -c "CREATE DATABASE flouze_test;"
- Redis: replaced by fakeredis (no real Redis needed for tests)
- JWT: RSA-2048 keys generated in-process for each test session
"""

import pytest
import pytest_asyncio
import fakeredis.aioredis as fakeredis
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = "postgresql+asyncpg://flouze:flouze@localhost:5432/flouze_test"


# ── RSA keys (generated once per session) ────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def configure_test_jwt():
    """Inject RSA-2048 test keys into settings so JWT operations work."""
    from app.core.config import settings

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings.jwt_private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    settings.jwt_public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


# ── Fake Redis (in-process, no daemon required) ───────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def fake_redis_setup():
    """Replace the Redis client with fakeredis for all tests."""
    import app.core.redis as redis_module

    fake = fakeredis.FakeRedis(decode_responses=True)
    redis_module._redis = fake
    yield fake
    redis_module._redis = None


# ── Test database ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    from app.models.base import Base

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


# ── HTTP client ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
