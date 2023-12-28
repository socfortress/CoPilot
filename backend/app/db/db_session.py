# ! Old Testing without Async
from contextlib import asynccontextmanager
from contextlib import contextmanager

from sqlmodel import Session
from sqlmodel import create_engine

from settings import SQLALCHEMY_DATABASE_URI

engine = create_engine(SQLALCHEMY_DATABASE_URI, connect_args={"check_same_thread": False})
session = "placeholder"

from contextlib import asynccontextmanager
from contextlib import contextmanager
from sqlmodel import Session

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from settings import SQLALCHEMY_DATABASE_URI

# create async engine for SQLite using aiosqlite
async_engine = create_async_engine(SQLALCHEMY_DATABASE_URI, echo=False)
sync_engine = create_engine(SQLALCHEMY_DATABASE_URI.replace("+aiosqlite", ""), echo=False)

# create a configured "AsyncSession" class
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
SyncSessionLocal = sessionmaker(bind=sync_engine, class_=Session, expire_on_commit=False)


@asynccontextmanager
async def get_db_session():
    """
    Context manager that provides an asynchronous database session.

    Yields:
        session: An asynchronous database session.

    Raises:
        Exception: If an error occurs during the database session.

    """
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


# Synchronous context manager to get DB session for each request
@contextmanager
def get_sync_db_session():
    """
    Context manager that provides a synchronous database session.

    Yields:
        SyncSessionLocal: The synchronous database session.

    Raises:
        Exception: If an error occurs during the session.
    """
    session = SyncSessionLocal()
    logger.info("Sync DB session created")
    try:
        yield session
    except Exception as e:
        logger.error(f"Error during sync DB session: {e}")
        session.rollback()
        raise e
    finally:
        logger.info("Closing sync DB session")
        session.close()

@asynccontextmanager
async def get_session():
    """
    Context manager that provides an async session object.

    Usage:
    async with get_session() as session:
        # Use the session object here
    """
    async with get_db_session() as session:
        yield session

async def get_db():
    """
    A coroutine function that returns an asynchronous context manager for a database session.

    Usage:
    async with get_db() as session:
        # Use the session object to interact with the database

    Returns:
    An asynchronous context manager that yields a database session object.
    """
    async with get_session() as session:
        yield session
