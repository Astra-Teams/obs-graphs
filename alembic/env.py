from sqlalchemy import create_engine, pool

from alembic import context
from src.obs_graphs.config import db_settings
from src.obs_graphs.db.database import Base

config = context.config

target_metadata = Base.metadata


def run_migrations_online() -> None:
    database_url = db_settings.database_url

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
