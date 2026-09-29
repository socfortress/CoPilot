from contextlib import asynccontextmanager
from typing import AsyncIterator
from typing import Optional

from fastapi import HTTPException
from fastapi import status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def internal_errors(action: str, session: Optional[AsyncSession] = None) -> AsyncIterator[None]:
    """Turn an unexpected failure into a generic 500 that still reads as ``Failed to <action>``.

    An ``HTTPException`` (a service's 403/404) passes through unchanged. Anything else
    is logged with its traceback and never returned: ``str(e)`` of a database error
    carries SQL, table and column names. With a ``session``, the failed transaction is
    rolled back first.
    """
    try:
        yield
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to {action}")
        if session is not None:
            await session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to {action}")
