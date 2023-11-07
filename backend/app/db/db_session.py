# ! Old Testing without Async
from contextlib import asynccontextmanager

from sqlmodel import Session
from sqlmodel import create_engine

from settings import SQLALCHEMY_DATABASE_URI

engine = create_engine(SQLALCHEMY_DATABASE_URI, connect_args={"check_same_thread": False})
# session = Session(bind=engine)
session = "placeholder"


#! New Testings with Async

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from settings import SQLALCHEMY_DATABASE_URI

# create async engine for SQLite using aiosqlite
async_engine = create_async_engine(SQLALCHEMY_DATABASE_URI, echo=True)

# create a configured "AsyncSession" class
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


# Dependency to get DB session for each request
# @asynccontextmanager
# async def get_db_session():
#     async with AsyncSessionLocal() as session:
#         yield session
@asynccontextmanager
async def get_db_session():
    async with AsyncSessionLocal() as session:
        logger.info("DB session created")
        try:
            yield session
        except Exception as e:
            logger.error(f"Error during DB session: {e}")
            await session.rollback()
            raise e
        finally:
            logger.info("Closing DB session")
            await session.close()


async def get_session():
    async with get_db_session() as session:
        return session
