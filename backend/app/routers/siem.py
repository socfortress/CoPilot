from fastapi import APIRouter

from app.siem.routes.event_sources import event_sources_router

# Instantiate the APIRouter
router = APIRouter()

router.include_router(event_sources_router, prefix="/siem/event_sources", tags=["SIEM - Event Sources"])
