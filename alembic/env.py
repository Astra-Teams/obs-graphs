from sqlalchemy import create_engine, pool

from alembic import context

# Import all models so they are registered with Base
from src.api.v1.models.workflow import Workflow, WorkflowStatus  # noqa: F401
from src.db.database import Base
from src.settings import get_settings

config = context.config

target_metadata = Base.metadata


def run_migrations_online() -> None:
    settings = get_settings()
    database_url = settings.DATABASE_URL

    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    pass  # Offline mode not implemented
else:
    run_migrations_online()
