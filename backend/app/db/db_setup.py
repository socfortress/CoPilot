from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

# ! New with Async
from sqlmodel import SQLModel

from app.auth.services.universal import create_admin_user
from app.auth.services.universal import create_scheduler_user
from app.auth.services.universal import remove_scheduler_user
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


async def create_roles(async_engine):
    """
    Creates roles in the database.

    Args:
        async_engine (AsyncEngine): The async engine used to connect to the database.

    Returns:
        None
    """
    logger.info("Creating roles")
    async with AsyncSession(async_engine) as session:  # Create an AsyncSession, not just a connection
        async with session.begin():  # Start a transaction
            await add_roles_if_not_exist(session)


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
