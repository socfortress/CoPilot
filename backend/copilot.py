import requests
import uvicorn
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseSettings
from sqlmodel import Session

from app.agents.routes.agents import agents_router
from app.auth.routes.auth import user_router
from app.auth.utils import AuthHandler
from app.connectors.cortex.routes.analyzers import cortex_analyzer_router
from app.connectors.dfir_iris.routes.alerts import dfir_iris_alerts_router
from app.connectors.dfir_iris.routes.assets import assets_router
from app.connectors.dfir_iris.routes.cases import cases_router
from app.connectors.dfir_iris.routes.notes import notes_router
from app.connectors.dfir_iris.routes.users import dfir_iris_users_router
from app.connectors.graylog.routes.collector import graylog_collector_router
from app.connectors.graylog.routes.events import graylog_events_router
from app.connectors.graylog.routes.management import graylog_management_router
from app.connectors.graylog.routes.monitoring import graylog_monitoring_router
from app.connectors.graylog.routes.pipelines import graylog_pipelines_router
from app.connectors.graylog.routes.streams import graylog_streams_router
from app.connectors.routes import connector_router
from app.connectors.shuffle.routes.workflows import shuffle_workflows_router
from app.connectors.sublime.routes.alerts import sublime_alerts_router
from app.connectors.velociraptor.routes.artifacts import velociraptor_artifacts_router
from app.connectors.wazuh_indexer.routes.alerts import wazuh_indexer_alerts_router

# from app.connectors.wazuh_indexer.routes.routes import wazuh_indexer_router
from app.connectors.wazuh_indexer.routes.monitoring import wazuh_indexer_router
from app.connectors.wazuh_manager.routes.rules import wazuh_manager_router
from app.customers.routes.customers import customers_router
from app.db.db_session import engine
from app.db.db_setup import create_tables
from app.healthchecks.agents.routes.agents import healtcheck_agents_router
from app.integrations.alert_escalation.routes.general_alert import (
    integration_general_alerts_router,
)
from app.integrations.dnstwist.routes.analyze import dnstwist_router
from app.middleware.logger import log_requests
from app.smtp.routes.configure import smtp_router
from app.utils import ErrorType
from app.utils import Logger
from app.utils import ValidationErrorItem
from app.utils import ValidationErrorResponse
from app.utils import logs_router
from settings import SQLALCHEMY_DATABASE_URI

auth_handler = AuthHandler()


app = FastAPI(description="CoPilot API", version="0.1.0", title="CoPilot API")

# Initialize the scheduler with your preferred settings
jobstores = {"default": SQLAlchemyJobStore(url=SQLALCHEMY_DATABASE_URI)}

# Initialize the scheduler with the job store
scheduler = AsyncIOScheduler(jobstores=jobstores)


# Define the function to be scheduled
def scheduled_task():
    # Replace with your actual endpoint you want to call
    response = requests.get("http://127.0.0.1:5000/agents/sync")
    # Log the response or perform actions as needed
    print(response.json())


# Allow all origins, methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


################## ! Middleware LOGGING TO `log_entry` table ! ##################
app.middleware("http")(log_requests)  # using the imported middleware


################## ! Exception Handlers ! ##################
# Utility function to get user_id from request
async def get_user_id_from_request(request: Request, session, logger_instance):
    return await logger_instance.get_user_id_from_request(request)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    with Session(engine) as session:
        logger_instance = Logger(session, auth_handler)
        user_id = await get_user_id_from_request(request, session, logger_instance)
        await logger_instance.log_error(user_id, request, exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    details = []

    for error in errors:
        field = error["loc"][-1]
        error_type = ErrorType(error["type"])
        details.append(ValidationErrorItem(field=field, error_type=error_type))

    # Extract the first message from details for use in ValidationErrorResponse
    main_message = details[0].message if details else "Validation Error"

    with Session(engine) as session:
        logger_instance = Logger(session, auth_handler)
        user_id = await get_user_id_from_request(request, session, logger_instance)
        await logger_instance.log_error(user_id, request, main_message)

    return JSONResponse(
        status_code=422,
        content=ValidationErrorResponse(message=main_message, details=details).dict(),
    )


################## ! INCLUDE ROUTES ! ##################
app.include_router(connector_router, prefix="/connectors", tags=["connectors"])
app.include_router(wazuh_indexer_router, prefix="/wazuh_indexer", tags=["wazuh-indexer"])
app.include_router(user_router, prefix="/auth", tags=["auth"])
app.include_router(wazuh_manager_router, prefix="/wazuh_manager", tags=["wazuh-manager"])
app.include_router(agents_router, prefix="/agents", tags=["agents"])
app.include_router(graylog_monitoring_router, prefix="/graylog", tags=["graylog"])
app.include_router(graylog_collector_router, prefix="/graylog", tags=["graylog"])
app.include_router(graylog_events_router, prefix="/graylog", tags=["graylog"])
app.include_router(graylog_pipelines_router, prefix="/graylog", tags=["graylog"])
app.include_router(graylog_streams_router, prefix="/graylog", tags=["graylog"])
app.include_router(graylog_management_router, prefix="/graylog", tags=["graylog"])
app.include_router(wazuh_indexer_alerts_router, prefix="/alerts", tags=["alerts"])
app.include_router(cases_router, prefix="/cases", tags=["cases"])
app.include_router(notes_router, prefix="/notes", tags=["notes"])
app.include_router(assets_router, prefix="/assets", tags=["assets"])
app.include_router(dfir_iris_alerts_router, prefix="/alerts", tags=["soc-alerts"])
app.include_router(dfir_iris_users_router, prefix="/users", tags=["dfir_iris-users"])
app.include_router(cortex_analyzer_router, prefix="/analyzers", tags=["cortex-analyzers"])
app.include_router(velociraptor_artifacts_router, prefix="/artifacts", tags=["velociraptor"])
app.include_router(shuffle_workflows_router, prefix="/workflows", tags=["shuffle"])
app.include_router(sublime_alerts_router, prefix="/sublime", tags=["sublime"])
app.include_router(customers_router, prefix="/customers", tags=["customers"])
app.include_router(healtcheck_agents_router, prefix="/healthcheck", tags=["healthcheck"])
app.include_router(smtp_router, prefix="/smtp", tags=["smtp"])
app.include_router(dnstwist_router, prefix="/dnstwist", tags=["dnstwist"])
app.include_router(integration_general_alerts_router, prefix="/alerts", tags=["alerts"])
app.include_router(logs_router, prefix="/logs", tags=["logs"])


@app.on_event("startup")
async def init_db():
    create_tables(engine)

    logger.info("Starting scheduler")
    scheduler.add_job(scheduled_task, "interval", minutes=1)
    scheduler.start()


@app.get("/")
def hello():
    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=5000)
