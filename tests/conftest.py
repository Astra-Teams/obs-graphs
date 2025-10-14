"""Shared test fixtures for all test categories."""

import os
import shutil
import uuid
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from src.obs_graphs.config import ObsGraphsSettings
from src.obs_graphs.db.database import Base, create_db_session, get_engine
from src.obs_graphs.main import app


@pytest.fixture(scope="session")
def default_settings() -> ObsGraphsSettings:
    """Provide a default Settings instance for tests."""

    return ObsGraphsSettings()


# Fixture paths
MOCKS_ROOT = Path("dev/mocks")


# =============================================================================
# Database Fixtures (used by db/ and e2e/ tests)
# =============================================================================


@pytest.fixture(scope="session")
def db_engine(default_settings: ObsGraphsSettings):
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

    if default_settings.use_sqlite:
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

    if default_settings.use_sqlite:
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
def vault_fixture(tmp_path: Path, default_settings: ObsGraphsSettings):
    """Copy the configured vault submodule (or a subpath) into a temp directory."""

    project_root = Path(__file__).resolve().parents[1]
    configured_path = Path(default_settings.vault_submodule_path)
    source_root = (
        configured_path
        if configured_path.is_absolute()
        else project_root / configured_path
    )

    if not source_root.exists():
        raise FileNotFoundError(
            f"Vault submodule not available at {source_root}. Please run 'git submodule update --init --recursive' to initialize submodules."
        )

    def _copy_vault(subpath: str | None = None) -> Path:
        source = source_root if subpath is None else source_root / subpath
        if not source.exists():
            if subpath is not None:
                source = source_root
            else:
                raise FileNotFoundError(f"Vault source path does not exist: {source}")

        destination_name = (subpath or "obsidian_vault").replace("/", "_")
        destination = tmp_path / f"{destination_name}_{uuid.uuid4().hex[:8]}"
        shutil.copytree(source, destination)
        return destination

    return _copy_vault


# =============================================================================
# Mock Data Fixtures (used by unit/ and e2e/ tests)
# =============================================================================


@pytest.fixture
def mock_data_path() -> Path:
    """Path to the mock data directory."""
    return MOCKS_ROOT
