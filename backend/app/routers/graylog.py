from fastapi import APIRouter

from app.connectors.graylog.routes.collector import graylog_collector_router
from app.connectors.graylog.routes.events import graylog_events_router
from app.connectors.graylog.routes.management import graylog_management_router
from app.connectors.graylog.routes.monitoring import graylog_monitoring_router
from app.connectors.graylog.routes.pipelines import graylog_pipelines_router
from app.connectors.graylog.routes.streams import graylog_streams_router

router = APIRouter()

router.include_router(graylog_collector_router, prefix="/graylog", tags=["graylog"])
router.include_router(graylog_events_router, prefix="/graylog", tags=["graylog"])
router.include_router(graylog_management_router, prefix="/graylog", tags=["graylog"])
router.include_router(graylog_monitoring_router, prefix="/graylog", tags=["graylog"])
router.include_router(graylog_streams_router, prefix="/graylog", tags=["graylog"])
router.include_router(graylog_pipelines_router, prefix="/graylog", tags=["graylog"])
