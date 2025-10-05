import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.settings import get_settings

# --- Lazy Initialization for Database Engine and Session Factory ---

_engine = None
_SessionLocal = None
_lock = threading.Lock()


def _initialize_factory():
    """
    Lazy initializer for the database engine and session factory.
    This prevents settings from being loaded at import time and is thread-safe.

    Database switching is controlled by DEBUG flag in settings.
    """
    global _engine, _SessionLocal
    with _lock:
        if _engine is None:
            settings = get_settings()

            # Use DEBUG flag to determine database type
            # DEBUG=True -> SQLite (offline development)
            # DEBUG=False -> PostgreSQL (production)
            if settings.DEBUG:
                # Use SQLite (for DEBUG mode or local testing)
                # test_db.sqlite3 file will be created in project root
                sqlite_file_path = "test_db.sqlite3"
                db_url = f"sqlite:///{sqlite_file_path}"

                # SQLite requires check_same_thread: False for FastAPI usage
                _engine = create_engine(
                    db_url, connect_args={"check_same_thread": False}
                )

            else:
                # Use PostgreSQL (for production/dev containers)
                if not settings.DATABASE_URL:
                    raise ValueError("DATABASE_URL must be set when DEBUG=False.")
                db_url = settings.DATABASE_URL
                _engine = create_engine(db_url, pool_pre_ping=True)

            _SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=_engine
            )


def create_db_session():
    """
    Creates a new SQLAlchemy session.
    For direct use in places like middleware or background tasks.
    """
    _initialize_factory()
    return _SessionLocal()


def get_db():
    """
    FastAPI dependency that provides a database session and ensures it's closed.
    """
    session = create_db_session()
    try:
        yield session
    finally:
        session.close()


# --- Declarative Base for Models ---

Base = declarative_base()


# Make Base and Engine accessible to external modules (especially test fixtures)
def get_engine():
    _initialize_factory()
    return _engine
