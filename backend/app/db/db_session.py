# ! NEW WITH MYSQL ! #

from contextlib import asynccontextmanager
from contextlib import contextmanager

# from settings import SQLALCHEMY_DATABASE_URI
from pathlib import Path

from environs import Env
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session
from sqlmodel import create_engine

env = Env()
env.read_env(Path(__file__).parent.parent / ".env")
# env.read_env(Path(__file__).parent.parent.parent / "docker-env" / ".env")
logger.info(f"Loading environment from {Path(__file__).parent.parent.parent.parent / '.env'}")

db_user = env.str("MYSQL_USER", default="copilot")
db_password = env.str("MYSQL_PASSWORD")
db_root_password = env.str("MYSQL_ROOT_PASSWORD")
db_url = env.str("MYSQL_URL", default="copilot-mysql")

logger.info(f"DB User: {db_user} and password: {db_password}")

# Update the SQLALCHEMY_DATABASE_URI to a MySQL compatible one in settings.py
# For this example, let's assume it has been updated. copilot-mysql
SQLALCHEMY_DATABASE_URI_NO_DB = f"mysql+pymysql://root:{db_root_password}@{db_url}"
SQLALCHEMY_DATABASE_URI = f"mysql+aiomysql://{db_user}:{db_password}@{db_url}/copilot"


session = "placeholder"

# Create async engine for MySQL using aiomysql
async_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URI,
    echo=False,
    # Additional MySQL-specific options can be set here if needed
)
# If you still need sync sessions for some operations, set it appropriately
# This would typically require a different sync driver since SQLAlchemy doesn't use aiomysql for sync operations
# ! THIS IS USED BY THE SCHEDULER ! #
sync_engine = create_engine(
    SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"),
    echo=False,
    # Additional MySQL-specific options can be set here if needed
)

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
