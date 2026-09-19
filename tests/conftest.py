import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Configure test environment
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["STORAGE_PATH"] = "./data/test_storage"
os.environ["AI_PROVIDER"] = "mock"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from app.core.security import get_password_hash, create_access_token
from app.db.base import Base
from app.db.models.user import User
from app.db.session import get_db
import app.db.session as db_session_module
from app.main import app

test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Bind global sessionmaker to test database during tests
db_session_module.engine = test_engine
db_session_module.AsyncSessionLocal = TestingAsyncSessionLocal


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Provides a fresh in-memory database session with clean schema per test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Creates a sample authenticated test user."""
    user = User(
        email="test_engineer@example.com",
        hashed_password=get_password_hash("SecretPassword123!"),
        full_name="Test Engineer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_user: User) -> dict:
    """Returns valid Bearer authorization header."""
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """Provides an AsyncClient bound to the test database session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
