import os
from logging.config import fileConfig

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from alembic import context

# Import your existing engine factory to automatically support DB_MODE switch
from storage.db_engine import get_engine

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    # Skip fileConfig if we're running programmatically and instructed to do so
    if config.attributes.get("configure_logger", True):
        fileConfig(config.config_file_name, disable_existing_loggers=False)

# Add your model's MetaData object here for 'autogenerate' support
# target_metadata = mymodel.Base.metadata
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable must be set for offline migrations")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Connectable is correctly resolved based on DB_MODE (standard vs cloudsql)
    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
