from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

# ! New with Async
from sqlmodel import SQLModel

from app.auth.services.universal import create_admin_user
from app.auth.services.universal import create_scheduler_user
from app.auth.services.universal import remove_scheduler_user
from app.db.db_populate import add_roles_if_not_exist

# from sqlalchemy import inspect
# from sqlmodel import Session
# from sqlmodel import SQLModel

# #from app.db.all_models import *
# from app.schedulers.models.scheduler import JobMetadata
# from app.db.db_populate import add_connectors_if_not_exist
# from app.db.db_populate import add_roles_if_not_exist

# ! Old without Async
# def create_tables(engine):
#     logger.info("Creating tables")

#     # Create an inspector object based on the engine
#     inspector = inspect(engine)

#     # Get the names of all tables in the database
#     existing_tables = inspector.get_table_names()

#     # Loop through all your models (tables)
#     for table in SQLModel.metadata.sorted_tables:
#         if table.name not in existing_tables:
#             # Only create the table if it doesn't exist
#             table.create(bind=engine)
#             logger.info(f"Table {table.name} created.")

#     # After creating all tables, add connectors if they don't exist
#     with Session(engine) as session:
#         add_connectors_if_not_exist(session)
#         add_roles_if_not_exist(session)
#         session.commit()


async def create_tables(async_engine):
    logger.info("Creating tables")
    async with async_engine.begin() as conn:
        # This will create all tables
        await conn.run_sync(SQLModel.metadata.create_all)


async def create_roles(async_engine):
    logger.info("Creating roles")
    async with AsyncSession(async_engine) as session:  # Create an AsyncSession, not just a connection
        async with session.begin():  # Start a transaction
            await add_roles_if_not_exist(session)


async def ensure_admin_user(async_engine):
    logger.info("Ensuring admin user exists")
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Pass the session to the inner function
            await create_admin_user(session)


async def ensure_scheduler_user(async_engine):
    logger.info("Ensuring scheduler user exists")
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Pass the session to the inner function
            await create_scheduler_user(session)


async def ensure_scheduler_user_removed(async_engine):
    logger.info("Ensuring scheduler user exists")
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Pass the session to the inner function
            await remove_scheduler_user(session)
