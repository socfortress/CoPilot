# ! NEW WITH MYSQL ! #

import ssl
from contextlib import asynccontextmanager
from contextlib import contextmanager

from loguru import logger
from sqlalchemy.engine.url import URL
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session
from sqlmodel import create_engine

from settings import DB_TLS
from settings import DB_TLS_CA
from settings import MAX_OVERFLOW
from settings import POOL_RECYCLE
from settings import POOL_SIZE
from settings import POOL_TIMEOUT
from settings import SQLALCHEMY_DATABASE_URI
from settings import TLS_VERIFY


# --- helper to map async → sync driver ---
def make_sync_uri(url: URL) -> str:
    backend = url.get_backend_name()
    driver = url.get_driver_name()

    if backend == "mysql" and driver == "aiomysql":
        url = url.set(drivername="mysql+pymysql")
    elif backend == "sqlite" and driver == "aiosqlite":
        url = url.set(drivername="sqlite")
    return str(url)


_url: URL = make_url(SQLALCHEMY_DATABASE_URI)
_backend = _url.get_backend_name()

async_connect_args: dict = {}
sync_connect_args: dict = {}

if DB_TLS and _backend == "mysql":
    if TLS_VERIFY:
        # Use system store when no custom CA is provided
        ssl_ctx = ssl.create_default_context(cafile=DB_TLS_CA or None)
        ssl_ctx.check_hostname = True
        logger.info("MySQL TLS enabled (verified)")
    else:
        ssl_ctx = ssl._create_unverified_context()
        logger.warning("MySQL TLS enabled (UNVERIFIED) — debug only")

    # Pass the same SSLContext to BOTH drivers:
    async_connect_args["ssl"] = ssl_ctx  # aiomysql expects SSLContext
    sync_connect_args["ssl"] = ssl_ctx  # PyMySQL accepts SSLContext, too
else:
    if DB_TLS and _backend != "mysql":
        logger.info(f"DB TLS requested but backend is '{_backend}'. Ignoring TLS connect args.")
    else:
        logger.info("DB TLS disabled")

# Async engine (aiomysql)
async_engine_kwargs = {
    "echo": False,
    "connect_args": async_connect_args,
    "pool_pre_ping": True,
}

if _backend == "mysql":
    async_engine_kwargs.update(
        pool_recycle=POOL_RECYCLE,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_use_lifo=True,
    )

async_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URI,
    **async_engine_kwargs,
)

# Sync engine (pymysql/sqlite)
sync_engine_kwargs = {
    "echo": False,
    "connect_args": sync_connect_args,
    "pool_pre_ping": True,
}

if _backend == "mysql":
    sync_engine_kwargs.update(
        pool_recycle=POOL_RECYCLE,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_use_lifo=True,
    )

sync_engine = create_engine(
    make_sync_uri(_url),
    **sync_engine_kwargs,
)

session = "placeholder"


# Create a configured "AsyncSession" class
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
SyncSessionLocal = sessionmaker(bind=sync_engine, class_=Session, expire_on_commit=False)


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


@contextmanager
def get_sync_db_session():
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
    async with get_db_session() as session:
        yield session


async def get_db():
    async with get_session() as session:
        yield session
