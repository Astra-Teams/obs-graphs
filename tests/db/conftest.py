import os
from typing import AsyncGenerator, Generator

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import get_settings
from src.db.database import Base, create_db_session, get_engine
from src.main import app

# Load .env and determine USE_SQLITE flag
load_dotenv()
settings = get_settings()
USE_SQLITE = settings.USE_SQLITE


@pytest.fixture(scope="session")
def db_engine():
    """
    Fixture that provides DB engine for the entire test session.
    USE_SQLITE=true case (sqlt-test):
        - Creates all tables (create_all) for SQLite DB and returns engine.
        - Drops all tables (drop_all) at session end.
    USE_SQLITE=false case (pstg-test):
        - Returns engine for PostgreSQL migrated by entrypoint.sh.
        - (Does not create/drop tables)
    """
    # Get engine initialized by application logic
    engine = get_engine()

    if USE_SQLITE:
        # For SQLite mode, create all tables from models before tests
        Base.metadata.create_all(bind=engine)

    yield engine

    if USE_SQLITE:
        # For SQLite mode, drop all tables after tests
        Base.metadata.drop_all(bind=engine)
        # Remove the SQLite file
        sqlite_file_path = "test_db.sqlite3"
        if os.path.exists(sqlite_file_path):
            os.remove(sqlite_file_path)

    # For PostgreSQL mode, DB is managed by container so do nothing
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Provides a transaction-scoped session for each test function.
    Tests run within transactions and are rolled back on completion,
    ensuring DB state independence between tests.
    """
    # Depend on db_engine fixture and share the initialized engine
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = SessionLocal()

    # Override FastAPI app's DI (get_db) with this test session
    app.dependency_overrides[create_db_session] = lambda: db

    try:
        yield db
    finally:
        db.rollback()  # Rollback all changes
        db.close()
        app.dependency_overrides.pop(create_db_session, None)


@pytest.fixture
async def client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """
    Creates httpx.AsyncClient configured for database-dependent tests.
    (Depends on db_session fixture to ensure DI override is applied)
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
