import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.auth.utils import AuthHandler
from app.db.db_session import async_engine
from app.db.db_setup import create_roles
from app.db.db_setup import create_tables
from app.db.db_setup import ensure_admin_user
from app.db.db_setup import ensure_scheduler_user
from app.db.db_setup import ensure_scheduler_user_removed
from app.middleware.exception_handlers import custom_http_exception_handler
from app.middleware.exception_handlers import validation_exception_handler
from app.middleware.logger import log_requests
from app.routers import agents
from app.routers import auth
from app.routers import connectors
from app.routers import cortex
from app.routers import customers
from app.routers import dfir_iris
from app.routers import dnstwist
from app.routers import graylog
from app.routers import healthcheck
from app.routers import logs
from app.routers import shuffle
from app.routers import smtp
from app.routers import sublime
from app.routers import velociraptor
from app.routers import wazuh_indexer
from app.routers import wazuh_manager
from app.schedulers.scheduler import init_scheduler

auth_handler = AuthHandler()


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


################## ! INCLUDE ROUTES ! ##################
app.include_router(connectors.router)
app.include_router(wazuh_indexer.router)
app.include_router(auth.router)
app.include_router(wazuh_manager.router)
app.include_router(agents.router)
app.include_router(graylog.router)
app.include_router(dfir_iris.router)
app.include_router(cortex.router)
app.include_router(velociraptor.router)
app.include_router(shuffle.router)
app.include_router(sublime.router)
app.include_router(customers.router)
app.include_router(healthcheck.router)
app.include_router(smtp.router)
app.include_router(dnstwist.router)
app.include_router(logs.router)


@app.on_event("startup")
async def init_db():
    # create_tables(engine)
    await create_tables(async_engine)
    await create_roles(async_engine)
    await ensure_admin_user(async_engine)
    await ensure_scheduler_user(async_engine)

    # Initialize the scheduler
    scheduler = init_scheduler()

    logger.info("Starting scheduler")
    if not scheduler.running:
        scheduler.start()


@app.get("/")
def hello():
    return {"message": "Hello World"}

@app.on_event("shutdown")
async def shutdown_scheduler():
    logger.info("Shutting down scheduler")
    # Initialize the scheduler
    scheduler = init_scheduler()
    if scheduler.running:
        scheduler.shutdown()

    await ensure_scheduler_user_removed(async_engine)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=5000)
