"""Application configuration.

Most configuration is set via environment variables.

For local development, use a .env file to set
environment variables.
"""
from pathlib import Path
from urllib.parse import quote_plus

from environs import Env
from loguru import logger

from app.utils import ensure_host_port

env = Env()
env.read_env(Path(__file__).parent.parent / ".env")
logger.info(f"Loading environment from {Path(__file__).parent.parent / '.env'}")

# Generic app settings
ENVIRONMENT: str = env.str("ENVIRONMENT", default="PRODUCTION")
SERVER_IP: str = env.str("SERVER_IP", default="localhost")
SERVER_PORT: int = env.int("SERVER_PORT", default=5000)
SECRET_KEY = env.str("SECRET_KEY", "not-a-secret")
MANAGED_DB: bool = env.bool("MANAGED_DB", default=False)
DEBUG: bool = env.bool("FLASK_DEBUG", default=False)

# Object Storage (MinIO / S3 compatible)
MINIO_ROOT_USER: str = env.str("MINIO_ROOT_USER", default="admin")
MINIO_ROOT_PASSWORD: str = env.str("MINIO_ROOT_PASSWORD", default="password")
MINIO_URL: str = env.str("MINIO_URL", default="copilot-minio")
MINIO_PORT: int = env.int("MINIO_PORT", default=9000)
MINIO_URL = ensure_host_port(MINIO_URL, MINIO_PORT)
MINIO_SECURE: bool = env.bool("MINIO_SECURE", default=False)
MINIO_REGION: str | None = env.str("MINIO_REGION", default="") or None

# TLS for MySQL
TLS_VERIFY: bool = env.bool("DB_TLS_VERIFY", default=False)
DB_TLS: bool = env.bool("DB_TLS", default=False)
DB_TLS_CA: str | None = env.str("DB_TLS_CA", default="") or None

# DSN strings
SQLALCHEMY_DATABASE_URI: str
SQLALCHEMY_DATABASE_URI_NO_DB: str | None

# Database config
mysql_user = env.str("MYSQL_USER", default="")
mysql_password = env.str("MYSQL_PASSWORD", default="")
mysql_url = env.str("MYSQL_URL", default="")
mysql_port = env.int("MYSQL_PORT", default=3306)
mysql_url = ensure_host_port(mysql_url, mysql_port) if mysql_url else mysql_url
mysql_db = env.str("MYSQL_DATABASE", default="copilot")
mysql_root_password = env.str("MYSQL_ROOT_PASSWORD", default="")

POOL_SIZE: int = env.int("DB_POOL_SIZE", 15)
MAX_OVERFLOW: int = env.int("DB_MAX_OVERFLOW", 15)
POOL_TIMEOUT: int = env.int("DB_POOL_TIMEOUT", 10)
POOL_RECYCLE: int = env.int("DB_POOL_RECYCLE", 1800)

if mysql_user and mysql_password and mysql_url:
    # Build DSN directly
    enc_user = quote_plus(mysql_user)
    enc_pass = quote_plus(mysql_password)
    SQLALCHEMY_DATABASE_URI = f"mysql+aiomysql://{enc_user}:{enc_pass}@{mysql_url}/{mysql_db}"

    # Only used if MANAGED_DB=false (bootstrap path). Leave None if you don't have a root/admin.
    SQLALCHEMY_DATABASE_URI_NO_DB = f"mysql+pymysql://root:{quote_plus(mysql_root_password)}@{mysql_url}" if mysql_root_password else None
else:
    basedir = Path().absolute()
    db_path = str(basedir / "data" / "copilot.db")
    SQLALCHEMY_DATABASE_URI = env.str(
        "SQLALCHEMY_DATABASE_URI",
        f"sqlite+aiosqlite:///{db_path}",
    )
    SQLALCHEMY_DATABASE_URI_NO_DB = None

SQLALCHEMY_TRACK_MODIFICATIONS: bool = env.bool(
    "SQLALCHEMY_TRACK_MODIFICATIONS",
    default=False,
)
