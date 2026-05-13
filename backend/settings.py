"""Application configuration.

Most configuration is set via environment variables.

For local development, use a .env file to set
environment variables.
"""
from pathlib import Path

from dotenv import load_dotenv
from environs import Env
from loguru import logger

# environs >= 14 stopped mutating os.environ from read_env() — values only land on the
# Env instance. Use python-dotenv to populate os.environ for the many os.environ.get()
# callsites across the app (notably _load_jwt_secret in app/auth/utils.py).
_DOTENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(_DOTENV_PATH)
env = Env()
logger.info(f"Loading environment from {_DOTENV_PATH}")


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
