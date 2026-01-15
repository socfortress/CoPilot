import os
import ssl

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
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
from app.db.db_populate import delete_connectors_if_exist
from app.schedulers.routes.scheduler import delete_job
from settings import DB_TLS
from settings import DB_TLS_CA
from settings import SQLALCHEMY_DATABASE_URI
from settings import TLS_VERIFY
from settings import mysql_password


def _tls_connect_args_for_url(url_str: str) -> dict:
    """
    Build connect_args for TLS only when using a MySQL driver.
    Uses settings.py: DB_TLS, TLS_VERIFY, DB_TLS_CA.
    """
    if not DB_TLS:
        return {}
    try:
        drivername = make_url(url_str).drivername  # e.g., 'mysql+pymysql'
    except Exception:
        drivername = ""
    if not drivername.startswith("mysql"):
        return {}

    if TLS_VERIFY:
        ctx = ssl.create_default_context(cafile=DB_TLS_CA or None)
        ctx.check_hostname = True
    else:
        ctx = ssl._create_unverified_context()
        ctx.check_hostname = False
    return {"ssl": ctx}


async def create_database_if_not_exists(db_url: str, db_name: str):
    """
    Create a database if it does not already exist.

    Args:
        db_url (str): Database URL to connect to MySQL server (without database part).
        db_name (str): The name of the database to create.
    """
    engine = create_engine(
        db_url,
        connect_args=_tls_connect_args_for_url(db_url),
    )
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
    engine = create_engine(
        db_url,
        connect_args=_tls_connect_args_for_url(db_url),
    )
    conn = engine.connect()
    try:
        # Check if user exists
        conn.execute("commit")
        exists = conn.execute(text(f"SELECT * FROM mysql.user WHERE user = '{db_user_name}';")).fetchone()
        if not exists:
            # Create user if it does not exist
            conn.execute("commit")
            conn.execute(text(f"CREATE USER '{db_user_name}'@'%' IDENTIFIED BY '{mysql_password}';"))
            logger.info(f"User '{db_user_name}' created successfully with password '{mysql_password}'.")
            conn.execute(text(f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user_name}'@'%';"))
            logger.info(f"User '{db_user_name}' created successfully and granted all privileges to the '{db_name}' database.")
        else:
            logger.info(f"User '{db_user_name}' already exists.")
    except SQLAlchemyError as e:
        logger.info(f"An error occurred: {e}")


# def apply_migrations():
#     """
#     Applies Alembic migrations to ensure the database schema is up to date.
#     """
#     logger.info("Applying migrations")

#     # Navigate up three levels from db_setup.py to the backend directory, then to the alembic directory
#     base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
#     alembic_directory = os.path.join(base_dir, "alembic")

#     logger.info(f"base_dir: {base_dir}")
#     logger.info(f"Alembic directory: {alembic_directory}")

#     alembic_cfg = Config(os.path.join(alembic_directory, "alembic.ini"))
#     alembic_cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))
#     alembic_cfg.set_main_option("script_location", alembic_directory)

#     # Apply migrations to the latest revision
#     try:
#         command.upgrade(alembic_cfg, "head")
#     except Exception as e:  # Catch any exception
#         logger.error(f"Error applying migrations: {e}")
#         raise e


# def apply_migrations():
#     """
#     Applies Alembic migrations to ensure the database schema is up to date.
#     """
#     logger.info("Applying migrations")

#     # Navigate up three levels from db_setup.py to the backend directory, then to the alembic directory
#     base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
#     alembic_directory = os.path.join(base_dir, "alembic")

#     logger.info(f"base_dir: {base_dir}")
#     logger.info(f"Alembic directory: {alembic_directory}")

#     alembic_cfg = Config(os.path.join(alembic_directory, "alembic.ini"))
#     alembic_cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))
#     alembic_cfg.set_main_option("script_location", alembic_directory)

#     # Check current revision first
#     logger.info("Checking current database revision...")
#     try:
#         from sqlalchemy import create_engine

#         from alembic.script import ScriptDirectory

#         # Get current revision
#         engine = create_engine(SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))
#         with engine.connect() as connection:
#             from alembic.runtime.migration import MigrationContext

#             context = MigrationContext.configure(connection)
#             current_rev = context.get_current_revision()
#             logger.info(f"Current database revision: {current_rev}")

#         # Get head revision
#         script = ScriptDirectory.from_config(alembic_cfg)
#         head_rev = script.get_current_head()
#         logger.info(f"Target head revision: {head_rev}")

#         if current_rev == head_rev:
#             logger.info("Database is already up to date!")
#             return

#     except Exception as e:
#         logger.warning(f"Could not check current revision: {e}")

#     # Apply migrations to the latest revision
#     logger.info("Starting migration upgrade...")
#     try:
#         command.upgrade(alembic_cfg, "head")
#         logger.info("Migrations completed successfully!")
#     except Exception as e:  # Catch any exception
#         logger.error(f"Error applying migrations: {e}")
#         raise e


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
    # Migrations use the sync driver
    pymysql_url = SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql")
    alembic_cfg.set_main_option("sqlalchemy.url", pymysql_url)
    alembic_cfg.set_main_option("script_location", alembic_directory)

    # Check current revision first (use TLS if configured)
    logger.info("Checking current database revision...")
    try:
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        engine = create_engine(
            pymysql_url,
            connect_args=_tls_connect_args_for_url(pymysql_url),
        )
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            logger.info(f"Current database revision: {current_rev}")

        # Get head revision
        script = ScriptDirectory.from_config(alembic_cfg)
        head_rev = script.get_current_head()
        logger.info(f"Target head revision: {head_rev}")

        if current_rev == head_rev:
            logger.info("Database is already up to date!")
            return

    except Exception as e:
        logger.warning(f"Could not check current revision: {e}")

    # Apply migrations to the latest revision
    logger.info("Starting migration upgrade...")
    try:
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed successfully!")
    except Exception as e:  # Catch any exception
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
    logger.info("Connectors added successfully")


async def delete_connectors(async_engine):
    """
    Deletes connectors from the database.

    Args:
        async_engine (AsyncEngine): The async engine used to connect to the database.

    Returns:
        None
    """
    logger.info("Deleting connectors")
    async with AsyncSession(
        async_engine,
    ) as session:  # Create an AsyncSession, not just a connection
        async with session.begin():  # Start a transaction
            await delete_connectors_if_exist(session)
    logger.info("Connectors deleted successfully")


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


async def delete_job_if_exists(async_engine):
    """
    Deletes a job from the database if it exists.

    Args:
        job_id (str): The ID of the job to delete.

    Returns:
        None
    """
    job_id = "wazuh_index_fields_resize"
    logger.info(f"Deleting job with ID {job_id}")
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Pass the session to the inner function
            await delete_job(session, job_id)


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
