from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

# ! New with Async
from sqlmodel import SQLModel

from app.auth.services.universal import create_admin_user
from app.auth.services.universal import create_scheduler_user
from app.auth.services.universal import remove_scheduler_user
from app.db.db_populate import add_available_integrations_auth_keys_if_not_exist
from app.db.db_populate import add_available_integrations_if_not_exist
from app.db.db_populate import add_connectors_if_not_exist
from app.db.db_populate import add_roles_if_not_exist


async def create_tables(async_engine):
    """
    Creates tables in the database.

    Args:
        async_engine (AsyncEngine): The async engine to connect to the database.

    Returns:
        None
    """
    logger.info("Creating tables")
    async with async_engine.begin() as conn:
        # This will create all tables
        await conn.run_sync(SQLModel.metadata.create_all)
    # Use AsyncSession for adding connectors
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            await add_connectors_if_not_exist(session)


async def update_tables(async_engine):
    """
    Updates tables in the database. Needed for adding new columns to existing tables.

    Args:
        async_engine (AsyncEngine): The async engine to connect to the database.

    Returns:
        None
    """
    logger.info("Updating tables")

    # Define the new columns to be added
    new_columns = {"scheduled_job_metadata": ["extra_data TEXT"]}

    async with async_engine.begin() as conn:
        for table_name, columns in new_columns.items():
            for column in columns:
                alter_table_query = text(f"ALTER TABLE {table_name} ADD COLUMN {column}")
                try:
                    await conn.execute(alter_table_query)
                except OperationalError as e:
                    if "duplicate column name" in str(e):
                        logger.info(f"Column {column} already exists in {table_name}")
                    else:
                        raise


async def create_roles(async_engine):
    """
    Creates roles in the database.

    Args:
        async_engine (AsyncEngine): The async engine used to connect to the database.

    Returns:
        None
    """
    logger.info("Creating roles")
    async with AsyncSession(
        async_engine,
    ) as session:  # Create an AsyncSession, not just a connection
        async with session.begin():  # Start a transaction
            await add_roles_if_not_exist(session)


async def create_available_integrations(async_engine):
    """
    Creates available integrations in the database.

    Args:
        async_engine (AsyncEngine): The async engine used to connect to the database.

    Returns:
        None
    """
    logger.info("Creating available integrations")
    async with AsyncSession(
        async_engine,
    ) as session:  # Create an AsyncSession, not just a connection
        async with session.begin():  # Start a transaction
            await add_available_integrations_if_not_exist(session)
            await add_available_integrations_auth_keys_if_not_exist(session)
            await session.commit()


async def ensure_admin_user(async_engine):
    """
    Ensures that an admin user exists in the database.

    Args:
        async_engine (AsyncEngine): The async engine used to connect to the database.

    Returns:
        None
    """
    logger.info("Ensuring admin user exists")
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Pass the session to the inner function
            await create_admin_user(session)


async def ensure_scheduler_user(async_engine):
    """
    Ensures that the scheduler user exists in the database.

    Args:
        async_engine (AsyncEngine): The async engine used to connect to the database.

    Returns:
        None
    """
    logger.info("Ensuring scheduler user exists")
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Pass the session to the inner function
            await create_scheduler_user(session)


async def ensure_scheduler_user_removed(async_engine):
    """
    Ensures that the scheduler user is removed from the database.

    Args:
        async_engine (AsyncEngine): The async engine used to connect to the database.

    Returns:
        None
    """
    logger.info("Ensuring scheduler user exists")
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Pass the session to the inner function
            await remove_scheduler_user(session)
