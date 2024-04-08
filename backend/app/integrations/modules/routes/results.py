from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.integrations.modules.schema.results import CopilotResponse
from loguru import logger

module_results_router = APIRouter()


@module_results_router.post("/results")
async def receive_results(data: CopilotResponse, session: AsyncSession = Depends(get_db)):
    logger.info(f"Received results: {data.dict()}")
    return {"message": "Results received successfully"}
