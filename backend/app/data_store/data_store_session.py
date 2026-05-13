from pathlib import Path

from dotenv import load_dotenv
from environs import Env
from loguru import logger
from miniopy_async import Minio

# Repo root is four parents up (backend/app/data_store/data_store_session.py).
# environs >= 14 stopped mutating os.environ from read_env(); use python-dotenv
# so os.environ.get() callsites elsewhere in the app see .env values.
_DOTENV_PATH = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(_DOTENV_PATH)
env = Env()
logger.info(f"Loading environment from {_DOTENV_PATH}")


minio_root_user = env.str("MINIO_ROOT_USER", default="admin")
minio_root_password = env.str("MINIO_ROOT_PASSWORD", default="password")
minio_url = env.str("MINIO_URL", default="copilot-minio")
minio_secure = env.bool("MINIO_SECURE", default=False)

logger.info(f"Minio Root User: {minio_root_user} and password: {minio_root_password}")


async def create_session() -> Minio:
    client = Minio(f"{minio_url}:9000", access_key=minio_root_user, secret_key=minio_root_password, secure=minio_secure)
    return client
