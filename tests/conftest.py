"""Shared test fixtures for all test categories."""

import os
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from src.db.database import Base, create_db_session, get_engine
from src.main import app
from src.settings import get_settings

# Load .env and determine settings
load_dotenv()
settings = get_settings()

# Fixture paths
MOCKS_ROOT = Path("dev/mocks")
VAULTS_ROOT = MOCKS_ROOT / "vault"


# =============================================================================
# Database Fixtures (used by db/ and e2e/ tests)
# =============================================================================


@pytest.fixture(scope="session")
def db_engine():
    """
    Fixture that provides DB engine for the entire test session.

    USE_SQLITE=true case (sqlt-test):
        - Creates all tables (create_all) for SQLite DB and returns engine.
        - Drops all tables (drop_all) at session end.
    USE_SQLITE=false case (pstg-test):
        - Returns engine for PostgreSQL migrated by entrypoint.sh.
        - Truncates all tables at session start to ensure clean state.
        - (Does not create/drop tables)
    """
    engine = get_engine()

    if settings.USE_SQLITE:
        # For SQLite mode, create all tables from models before tests
        Base.metadata.create_all(bind=engine)
    else:
        # For PostgreSQL mode, truncate all tables to ensure clean state
        with engine.connect() as conn:
            # Disable foreign key checks temporarily
            conn.execute(text("SET session_replication_role = 'replica';"))
            # Truncate all tables
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE;'))
            # Re-enable foreign key checks
            conn.execute(text("SET session_replication_role = 'origin';"))
            conn.commit()

    yield engine

    if settings.USE_SQLITE:
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

    Depends on db_session fixture to ensure DI override is applied.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# =============================================================================
# Vault Fixtures (used by e2e/ and unit/ tests)
# =============================================================================


@pytest.fixture
def vault_fixture(tmp_path: Path):
    """
    Provides a function to copy vault fixtures to tmp_path.

    Usage:
        def test_something(vault_fixture):
            vault_path = vault_fixture("empty_vault")
            # ... test code ...
    """

    def _copy_vault(fixture_name: str) -> Path:
        """Copy a vault fixture to tmp_path and return its path."""
        source = VAULTS_ROOT / fixture_name
        destination = tmp_path / fixture_name
        shutil.copytree(source, destination)
        return destination

    return _copy_vault


# =============================================================================
# Mock Data Fixtures (used by unit/ and e2e/ tests)
# =============================================================================


@pytest.fixture
def mock_data_path() -> Path:
    """Provides the path to the mock data directory."""
    return MOCKS_ROOT


@pytest.fixture
def llm_responses(mock_data_path: Path) -> dict:
    """Load LLM mock responses from JSON file."""
    import json

    llm_responses_file = mock_data_path / "llm_responses.json"
    return json.loads(llm_responses_file.read_text(encoding="utf-8"))


@pytest.fixture
def github_responses(mock_data_path: Path) -> dict:
    """Load GitHub mock responses from JSON file."""
    import json

    github_responses_file = mock_data_path / "github_responses.json"
    return json.loads(github_responses_file.read_text(encoding="utf-8"))
