import os

import uvicorn
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from sqlalchemy import text
from sqlalchemy.engine.url import make_url

from app.auth.utils import AuthHandler
from app.data_store.data_store_setup import create_buckets
from app.db.db_session import async_engine
from app.db.db_setup import add_connectors
from app.db.db_setup import apply_migrations
from app.db.db_setup import create_available_integrations
from app.db.db_setup import create_available_network_connectors
from app.db.db_setup import create_copilot_user_if_not_exists
from app.db.db_setup import create_database_if_not_exists
from app.db.db_setup import create_roles
from app.db.db_setup import delete_connectors
from app.db.db_setup import ensure_admin_user
from app.db.db_setup import ensure_scheduler_user
from app.db.db_setup import ensure_scheduler_user_removed
from app.middleware.exception_handlers import custom_http_exception_handler
from app.middleware.exception_handlers import validation_exception_handler
from app.middleware.exception_handlers import value_error_handler

# from app.routers import ask_socfortress
from app.routers import active_response
from app.routers import agents
from app.routers import alert_creation_settings
from app.routers import auth
from app.routers import bitdefender
from app.routers import carbonblack
from app.routers import cato
from app.routers import connectors
from app.routers import copilot_action
from app.routers import copilot_mcp
from app.routers import cortex
from app.routers import crowdstrike
from app.routers import customer_provisioning
from app.routers import customers
from app.routers import darktrace
from app.routers import defenderforendpoint
from app.routers import dfir_iris
from app.routers import dnstwist
from app.routers import duo
from app.routers import grafana
from app.routers import graylog
from app.routers import healthcheck
from app.routers import huntress
from app.routers import incidents
from app.routers import influxdb
from app.routers import integrations
from app.routers import license
from app.routers import logs
from app.routers import mimecast
from app.routers import modules
from app.routers import monitoring_alert
from app.routers import network_connectors
from app.routers import nuclei
from app.routers import office365
from app.routers import portainer
from app.routers import sap_siem
from app.routers import scheduler
from app.routers import scoutsuite
from app.routers import shuffle
from app.routers import smtp
from app.routers import stack_provisioning
from app.routers import sublime
from app.routers import threat_intel
from app.routers import velociraptor
from app.routers import wazuh_indexer
from app.routers import wazuh_manager
from app.schedulers.scheduler import get_scheduler_instance
from app.schedulers.scheduler import init_scheduler
from settings import ENVIRONMENT
from settings import MANAGED_DB
from settings import SERVER_IP
from settings import SERVER_PORT
from settings import SQLALCHEMY_DATABASE_URI_NO_DB

# from app.middleware.logger import log_requests


auth_handler = AuthHandler()

# ! Not needed for now maybe revist later ! #
# ssl_keyfile = os.path.join(os.path.dirname(__file__), "../nginx/server.key")
# ssl_certfile = os.path.join(os.path.dirname(__file__), "../nginx/server.crt")

app = FastAPI(description="CoPilot API", version="0.1.0", title="CoPilot API")

# Create an APIRouter with a prefix of `/api`
api_router = APIRouter(prefix="/api")


# Allow all origins, methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


################## ! Middleware LOGGING TO `log_entry` table ! ##################
# Comment out logging for now, not sure I want to use it
# app.middleware("http")(log_requests)  # using the imported middleware


################## ! Exception Handlers ! ##################
app.add_exception_handler(HTTPException, custom_http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)


################## ! INCLUDE ROUTES ! ##################
api_router.include_router(connectors.router)
api_router.include_router(wazuh_indexer.router)
api_router.include_router(auth.router)
api_router.include_router(cato.router)
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
# ! Commenting out for now, will revist later if needed ! #
# api_router.include_router(ask_socfortress.router)
api_router.include_router(alert_creation_settings.router)
api_router.include_router(integrations.router)
api_router.include_router(office365.router)
api_router.include_router(copilot_action.router)
api_router.include_router(copilot_mcp.router)
api_router.include_router(mimecast.router)
api_router.include_router(scheduler.router)
api_router.include_router(monitoring_alert.router)
api_router.include_router(sap_siem.router)
api_router.include_router(stack_provisioning.router)
api_router.include_router(active_response.router)
api_router.include_router(huntress.router)
api_router.include_router(license.router)
api_router.include_router(modules.router)
api_router.include_router(carbonblack.router)
api_router.include_router(network_connectors.router)
api_router.include_router(crowdstrike.router)
api_router.include_router(bitdefender.router)
api_router.include_router(scoutsuite.router)
api_router.include_router(nuclei.router)
api_router.include_router(duo.router)
api_router.include_router(portainer.router)
api_router.include_router(incidents.router)
api_router.include_router(darktrace.router)
api_router.include_router(defenderforendpoint.router)

# Include the APIRouter in the FastAPI app
app.include_router(api_router)


@app.on_event("startup")
async def init_db():
    logger.info("Initializing database")

    # Run DB bootstrap only when:
    #  - we're in PRODUCTION
    #  - MANAGED_DB is false (self-hosted bootstrap allowed)
    #  - and the NO_DB URI exists and is a MySQL DSN (not SQLite)
    should_bootstrap = False
    if ENVIRONMENT == "PRODUCTION" and not MANAGED_DB:
        if SQLALCHEMY_DATABASE_URI_NO_DB:
            try:
                url = make_url(SQLALCHEMY_DATABASE_URI_NO_DB)
                # url.get_backend_name() returns "mysql", "sqlite", etc.
                should_bootstrap = url.get_backend_name() == "mysql"
            except Exception as e:
                logger.warning(f"Skipping bootstrap: invalid NO_DB URI ({e})")

    if should_bootstrap:
        await create_database_if_not_exists(
            db_url=SQLALCHEMY_DATABASE_URI_NO_DB,
            db_name="copilot",
        )
        await create_copilot_user_if_not_exists(
            db_url=SQLALCHEMY_DATABASE_URI_NO_DB,
            db_user_name="copilot",
        )

    # connectivity preflight guard
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connectivity preflight: OK")
    except Exception as e:
        logger.error(f"Database connectivity preflight FAILED: {e}")
        raise e

    apply_migrations()
    await create_buckets()
    await add_connectors(async_engine)
    await delete_connectors(async_engine)
    await create_roles(async_engine)
    await create_available_integrations(async_engine)
    await create_available_network_connectors(async_engine)
    await ensure_admin_user(async_engine)
    await ensure_scheduler_user(async_engine)

    # Initialize the scheduler
    scheduler = await init_scheduler()

    if not scheduler.running:
        logger.info("Scheduler is not running, starting now...")
        scheduler.start()


# Create `scoutsuite-report` directory if it doesnt exist
if not os.path.exists("scoutsuite-report"):
    os.makedirs("scoutsuite-report")

app.mount("/scoutsuite-report", StaticFiles(directory="scoutsuite-report"), name="scoutsuite-report")


@app.get("/")
def hello():
    return {"message": "CoPilot - We Made It!"}


@app.on_event("shutdown")
async def shutdown_scheduler():
    logger.info("Shutting down scheduler")
    # Initialize the scheduler
    scheduler = await get_scheduler_instance()
    if scheduler.running:
        logger.info("Scheduler is running, shutting down now...")
        scheduler.shutdown()

    await ensure_scheduler_user_removed(async_engine)

    await async_engine.dispose()


if __name__ == "__main__":
    uvicorn.run(app, host=SERVER_IP, port=SERVER_PORT)
