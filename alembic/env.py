import asyncio
from logging.config import fileConfig
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from app.config import settings
from app.models import quiz,user
from sqlmodel import SQLModel
from app.db import create_async_engine
target_metadata = SQLModel.metadata
#target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# Common migration function for online mode (used by run_sync)
def do_run_migrations(connection):
    """Run migrations in 'online' mode using a live connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,      # detect column type changes
        render_as_batch=True    # useful for SQLite, harmless elsewhere
    )
    with context.begin_transaction():
        context.run_migrations()

        
# Async online migration function

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with asyncpg."""

    db_url_str = str(settings.DATABASE_URL)
    connect_args = {}

    # Parse DB URL and adjust for asyncpg
    parsed_url = urlparse(db_url_str)
    scheme = parsed_url.scheme
    if scheme == "postgresql":
        scheme = "postgresql+asyncpg"

    current_query_params = parse_qs(parsed_url.query)
    new_query_params = {}

    for key, value in current_query_params.items():
        if key.lower() == "sslmode" and value[0] == "require":
            connect_args["ssl"] = True
        else:
            new_query_params[key] = value[0]

    cleaned_query_string = urlencode(new_query_params)
    final_url_str = urlunparse((
        scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        cleaned_query_string,
        parsed_url.fragment,
    ))

    connectable = create_async_engine(final_url_str, connect_args=connect_args)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

    



if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
