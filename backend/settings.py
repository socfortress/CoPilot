"""Application configuration.

Most configuration is set via environment variables.

For local development, use a .env file to set
environment variables.
"""
from pathlib import Path
from loguru import logger

from environs import Env

env = Env()
env.read_env(Path(__file__).parent.parent / ".env")
logger.info(f"Loading environment from {Path(__file__).parent.parent / '.env'}")



basedir = Path().absolute()
db_path = str(basedir / "copilot.db")

ENV = env.str("SECRET_KEY", default="production")
DEBUG = env.bool("FLASK_DEBUG", default=False)
SECRET_KEY = env.str("SECRET_KEY", "not-a-secret")
# SQLALCHEMY_DATABASE_URI = env.str("SQLALCHEMY_DATABASE_URI", f"sqlite:///{db_path}")
SQLALCHEMY_DATABASE_URI = env.str("SQLALCHEMY_DATABASE_URI", f"sqlite+aiosqlite:///{db_path}")
SQLALCHEMY_TRACK_MODIFICATIONS = env.bool(
    "SQLALCHEMY_TRACK_MODIFICATIONS",
    default=False,
)
UPLOAD_FOLDER = env.str("UPLOAD_FOLDER", str(Path.home() / "Desktop/copilot_uploads"))
