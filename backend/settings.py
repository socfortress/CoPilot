"""Application configuration.

Most configuration is set via environment variables.

For local development, use a .env file to set
environment variables.
"""
from pathlib import Path

from environs import Env
from loguru import logger

env = Env()
env.read_env(Path(__file__).parent.parent / ".env")
# env.read_env(Path(__file__).parent.parent.parent / "docker-env" / ".env")
logger.info(f"Loading environment from {Path(__file__).parent.parent / '.env'}")
# logger.info(f"Loading environment from {Path(__file__).parent.parent.parent / 'docker-env' / '.env'}")


basedir = Path().absolute()
db_path = str(basedir / "data" / "copilot.db")

ENV = env.str("SECRET_KEY", default="production")
DEBUG = env.bool("FLASK_DEBUG", default=False)
SECRET_KEY = env.str("SECRET_KEY", "not-a-secret")
# SQLALCHEMY_DATABASE_URI = env.str("SQLALCHEMY_DATABASE_URI", f"sqlite:///{db_path}")
SQLALCHEMY_DATABASE_URI = env.str(
    "SQLALCHEMY_DATABASE_URI",
    f"sqlite+aiosqlite:///{db_path}",
)
SQLALCHEMY_TRACK_MODIFICATIONS = env.bool(
    "SQLALCHEMY_TRACK_MODIFICATIONS",
    default=False,
)
