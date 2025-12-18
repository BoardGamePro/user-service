import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.dependencies import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture()
def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)

    async def create_tables():
        from app.database import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    import asyncio
    asyncio.get_event_loop().run_until_complete(create_tables())

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    yield SessionLocal
    asyncio.get_event_loop().run_until_complete(engine.dispose())

@pytest.fixture(autouse=True)
def override_get_db(db_session):
    async def _override_get_db():
        async with db_session() as session:
            yield session
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest_asyncio.fixture(scope="function")
async def setup_clean_test_data(db_session):
    from sqlalchemy import text
    async with db_session() as db:
        await db.execute(
            text("DELETE FROM comments WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@example.com')"))
        await db.execute(text("DELETE FROM tokens WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@example.com')"))
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))
        await db.commit()
    yield
    async with db_session() as db:
        await db.execute(
            text("DELETE FROM comments WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@example.com')"))
        await db.execute(text("DELETE FROM tokens WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@example.com')"))
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))
        await db.commit()
