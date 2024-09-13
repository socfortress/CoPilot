from miniopy_async import Minio

from pathlib import Path

from environs import Env
from loguru import logger


env = Env()
env.read_env(Path(__file__).parent.parent / ".env")
# env.read_env(Path(__file__).parent.parent.parent / "docker-env" / ".env")
logger.info(f"Loading environment from {Path(__file__).parent.parent.parent.parent / '.env'}")


minio_root_user = env.str("MINIO_ROOT_USER", default="admin")
minio_root_password = env.str("MINIO_ROOT_PASSWORD")
minio_url = env.str("MINIO_URL", default="copilot-minio")

logger.info(f"Minio Root User: {minio_root_user} and password: {minio_root_password}")

async def create_session() -> Minio:
    client = Minio(
        f'{minio_url}:9000',
        access_key=minio_root_user,
        secret_key=minio_root_password,
        secure=False  # Set to True if using HTTPS
    )
    return client







