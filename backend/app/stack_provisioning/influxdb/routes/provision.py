from fastapi import APIRouter
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.stack_provisioning.influxdb.schema.provision import (
    AvailableInfluxDBChecksResponse,
)
from app.stack_provisioning.influxdb.schema.provision import (
    ProvisionInfluxDBAllChecksRequest,
)
from app.stack_provisioning.influxdb.schema.provision import (
    ProvisionInfluxDBCheckRequest,
)
from app.stack_provisioning.influxdb.schema.provision import ProvisionInfluxDBResponse
from app.stack_provisioning.influxdb.services.provision import get_available_checks
from app.stack_provisioning.influxdb.services.provision import provision_all_checks
from app.stack_provisioning.influxdb.services.provision import provision_check

stack_provisioning_influxdb_router = APIRouter()


@stack_provisioning_influxdb_router.get(
    "/influxdb/available/checks",
    response_model=AvailableInfluxDBChecksResponse,
    description="Get the InfluxDB monitoring checks available for provisioning",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_available_checks_route() -> AvailableInfluxDBChecksResponse:
    """
    Get the InfluxDB monitoring checks available for provisioning
    """
    logger.info("Getting available InfluxDB checks...")
    return await get_available_checks()


@stack_provisioning_influxdb_router.post(
    "/influxdb/provision/check",
    response_model=ProvisionInfluxDBResponse,
    description="Provision a monitoring check in the InfluxDB instance",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_check_route(
    check_request: ProvisionInfluxDBCheckRequest,
) -> ProvisionInfluxDBResponse:
    """
    Provision a monitoring check in the InfluxDB instance
    """
    logger.info(f"Provisioning InfluxDB check {check_request.check_name.name}...")
    return await provision_check(check_request)


@stack_provisioning_influxdb_router.post(
    "/influxdb/provision/checks",
    response_model=ProvisionInfluxDBResponse,
    description="Provision all available monitoring checks in the InfluxDB instance",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def provision_all_checks_route(
    check_request: ProvisionInfluxDBAllChecksRequest,
) -> ProvisionInfluxDBResponse:
    """
    Provision all available monitoring checks in the InfluxDB instance
    """
    logger.info("Provisioning all InfluxDB checks...")
    return await provision_all_checks(check_request.overwrite)
