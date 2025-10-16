import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import DATABASE_URL
from app.main import app
from app.dependencies import get_db

@pytest.fixture()
def db_session():
    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    yield SessionLocal
    import asyncio
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
        await db.execute(text("DELETE FROM tokens WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@example.com')"))
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))
        await db.commit()
    yield
    # Очистка после теста
    async with db_session() as db:
        await db.execute(text("DELETE FROM tokens WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%@example.com')"))
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))
        await db.commit()
