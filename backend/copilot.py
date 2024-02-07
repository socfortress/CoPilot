import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.auth.utils import AuthHandler
from app.db.db_session import async_engine
from app.db.db_setup import create_available_integrations
from app.db.db_setup import create_roles
from app.db.db_setup import create_tables
from app.db.db_setup import ensure_admin_user
from app.db.db_setup import ensure_scheduler_user
from app.db.db_setup import ensure_scheduler_user_removed
from app.middleware.exception_handlers import custom_http_exception_handler
from app.middleware.exception_handlers import validation_exception_handler
from app.middleware.exception_handlers import value_error_handler
from app.middleware.logger import log_requests
from app.routers import agents
from app.routers import alert_creation
from app.routers import alert_creation_settings
from app.routers import ask_socfortress
from app.routers import auth
from app.routers import connectors
from app.routers import cortex
from app.routers import customer_provisioning
from app.routers import customers
from app.routers import dfir_iris
from app.routers import dnstwist
from app.routers import grafana
from app.routers import graylog
from app.routers import healthcheck
from app.routers import influxdb
from app.routers import integrations
from app.routers import logs
from app.routers import mimecast
from app.routers import monitoring_alert
from app.routers import office365
from app.routers import scheduler
from app.routers import shuffle
from app.routers import smtp
from app.routers import sublime
from app.routers import threat_intel
from app.routers import velociraptor
from app.routers import wazuh_indexer
from app.routers import wazuh_manager
from app.schedulers.scheduler import init_scheduler

auth_handler = AuthHandler()
# Get the `SERVER_IP` from the `.env` file
load_dotenv()
server_ip = os.getenv("SERVER_IP", "localhost")

app = FastAPI(description="CoPilot API", version="0.1.0", title="CoPilot API")


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
app.add_exception_handler(HTTPException, custom_http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)

# Step 1: Create an APIRouter with a prefix of `/api`
api_router = APIRouter(prefix="/api")

################## ! INCLUDE ROUTES ! ##################
api_router.include_router(connectors.router)
api_router.include_router(wazuh_indexer.router)
api_router.include_router(auth.router)
api_router.include_router(wazuh_manager.router)
api_router.include_router(agents.router)
api_router.include_router(graylog.router)
api_router.include_router(dfir_iris.router)
api_router.include_router(cortex.router)
api_router.include_router(velociraptor.router)
api_router.include_router(shuffle.router)
api_router.include_router(sublime.router)
api_router.include_router(customers.router)
api_router.include_router(healthcheck.router)
api_router.include_router(smtp.router)
api_router.include_router(dnstwist.router)
api_router.include_router(logs.router)
api_router.include_router(influxdb.router)
api_router.include_router(grafana.router)
api_router.include_router(customer_provisioning.router)
api_router.include_router(threat_intel.router)
api_router.include_router(ask_socfortress.router)
api_router.include_router(alert_creation.router)
api_router.include_router(alert_creation_settings.router)
api_router.include_router(integrations.router)
api_router.include_router(office365.router)
api_router.include_router(mimecast.router)
api_router.include_router(scheduler.router)
api_router.include_router(monitoring_alert.router)

# Include the APIRouter in the FastAPI app
app.include_router(api_router)


@app.on_event("startup")
async def init_db():
    # create_tables(engine)
    await create_tables(async_engine)
    await create_roles(async_engine)
    await create_available_integrations(async_engine)
    await ensure_admin_user(async_engine)
    await ensure_scheduler_user(async_engine)

    # Initialize the scheduler
    scheduler = init_scheduler()

    logger.info("Starting scheduler")
    if not scheduler.running:
        scheduler.start()


@app.get("/")
def hello():
    return {"message": "CoPilot - We Made It!"}


@app.on_event("shutdown")
async def shutdown_scheduler():
    logger.info("Shutting down scheduler")
    # Initialize the scheduler
    scheduler = init_scheduler()
    if scheduler.running:
        scheduler.shutdown()

    await ensure_scheduler_user_removed(async_engine)


if __name__ == "__main__":
    uvicorn.run(app, host=server_ip, port=5000)
