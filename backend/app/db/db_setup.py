import os

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

# ! New with Async
from sqlmodel import SQLModel

from alembic import command
from alembic.config import Config
from app.auth.services.universal import create_admin_user
from app.auth.services.universal import create_scheduler_user
from app.auth.services.universal import remove_scheduler_user
from app.db.db_populate import add_available_integrations_auth_keys_if_not_exist
from app.db.db_populate import add_available_integrations_if_not_exist
from app.db.db_populate import add_available_network_connectors_auth_keys_if_not_exist
from app.db.db_populate import add_available_network_connectors_if_not_exist
from app.db.db_populate import add_connectors_if_not_exist
from app.db.db_populate import add_roles_if_not_exist
from app.db.db_session import SQLALCHEMY_DATABASE_URI
from app.db.db_session import db_password


async def create_database_if_not_exists(db_url: str, db_name: str):
    """
    Create a database if it does not already exist.

    Args:
        db_url (str): Database URL to connect to MySQL server (without database part).
        db_name (str): The name of the database to create.
    """
    engine = create_engine(db_url)
    conn = engine.connect()
    try:
        # Check if database exists
        conn.execute("commit")
        exists = conn.execute(text(f"SHOW DATABASES LIKE '{db_name}';")).fetchone()
        if not exists:
            # Create database if it does not exist
            conn.execute("commit")
            conn.execute(text(f"CREATE DATABASE {db_name};"))
            logger.info(f"Database '{db_name}' created successfully.")
        else:
            logger.info(f"Database '{db_name}' already exists.")
    except SQLAlchemyError as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()
        engine.dispose()


async def create_copilot_user_if_not_exists(db_url: str, db_user_name: str):
    """
    Create a user if it does not already exist.

    Args:
        db_url (str): Database URL to connect to MySQL server (without database part).
        db_user_name (str): The name of the user to create.
    """
    db_name = "copilot"
    engine = create_engine(db_url)
    conn = engine.connect()
    try:
        # Check if user exists
        conn.execute("commit")
        exists = conn.execute(text(f"SELECT * FROM mysql.user WHERE user = '{db_user_name}';")).fetchone()
        if not exists:
            # Create user if it does not exist
            conn.execute("commit")
            conn.execute(text(f"CREATE USER '{db_user_name}'@'%' IDENTIFIED BY '{db_password}';"))
            logger.info(f"User '{db_user_name}' created successfully with password '{db_password}'.")
            conn.execute(text(f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user_name}'@'%';"))
            logger.info(f"User '{db_user_name}' created successfully and granted all privileges to the '{db_name}' database.")
        else:
            logger.info(f"User '{db_user_name}' already exists.")
    except SQLAlchemyError as e:
        logger.info(f"An error occurred: {e}")


def apply_migrations():
    """
    Applies Alembic migrations to ensure the database schema is up to date.
    """
    logger.info("Applying migrations")

    # Navigate up three levels from db_setup.py to the backend directory, then to the alembic directory
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    alembic_directory = os.path.join(base_dir, "alembic")

    logger.info(f"base_dir: {base_dir}")
    logger.info(f"Alembic directory: {alembic_directory}")

    alembic_cfg = Config(os.path.join(alembic_directory, "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))
    alembic_cfg.set_main_option("script_location", alembic_directory)

    # Apply migrations to the latest revision
    try:
        command.upgrade(alembic_cfg, "head")
    except OperationalError as e:
        logger.error(f"Error applying migrations: {e}")
        raise e


async def add_connectors(async_engine):
    """
    Adds connectors to the database.

    Args:
        async_engine (AsyncEngine): The async engine used to connect to the database.

    Returns:
        None
    """
    logger.info("Adding connectors")
    async with AsyncSession(
        async_engine,
    ) as session:  # Create an AsyncSession, not just a connection
        async with session.begin():  # Start a transaction
            await add_connectors_if_not_exist(session)


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
    new_columns = {
        "scheduled_job_metadata": ["extra_data TEXT"],
        "customer_provisioning_default_settings": ["wazuh_worker_hostname TEXT"],
        "agents": ["wazuh_agent_status TEXT"],
    }

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
        try:
            await add_available_integrations_if_not_exist(session)
            await add_available_integrations_auth_keys_if_not_exist(session)
        except Exception as e:
            logger.error(f"Error creating available integrations: {e}")
            await session.rollback()  # Explicit rollback on error
            raise  # Re-raise the exception to handle it further up the call stack
        else:
            await session.commit()  # Explicit commit if all operations are successful


async def create_available_network_connectors(async_engine):
    """
    Creates available network connectors in the database.

    Args:
        async_engine (AsyncEngine): The async engine used to connect to the database.

    Returns:
        None
    """
    logger.info("Creating available network connectors")
    async with AsyncSession(
        async_engine,
    ) as session:  # Create an AsyncSession, not just a connection
        try:
            await add_available_network_connectors_if_not_exist(session)
            await add_available_network_connectors_auth_keys_if_not_exist(session)
        except Exception as e:
            logger.error(f"Error creating available integrations: {e}")
            await session.rollback()  # Explicit rollback on error
            raise  # Re-raise the exception to handle it further up the call stack
        else:
            await session.commit()  # Explicit commit if all operations are successful


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
