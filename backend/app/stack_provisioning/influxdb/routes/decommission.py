from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.stack_provisioning.influxdb.schema.provision import AvailableInfluxDBChecks
from app.stack_provisioning.influxdb.schema.provision import (
    DecommissionInfluxDBCheckResponse,
)
from app.stack_provisioning.influxdb.services.provision import decommission_check

stack_decommissioning_influxdb_router = APIRouter()


@stack_decommissioning_influxdb_router.delete(
    "/influxdb/check/{check_name}",
    response_model=DecommissionInfluxDBCheckResponse,
    description="Delete a provisioned monitoring check from the InfluxDB instance",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def decommission_check_route(check_name: str) -> DecommissionInfluxDBCheckResponse:
    """
    Delete a provisioned monitoring check from the InfluxDB instance.

    `check_name` is the template name (e.g. `SOCFORTRESS_INFLUXDB_CPU_CHECK`), not the
    name the check carries inside InfluxDB — so only checks CoPilot knows how to
    provision can be removed through this route.
    """
    if check_name not in AvailableInfluxDBChecks.__members__:
        raise HTTPException(
            status_code=400,
            detail=f"Check {check_name} is not available. Please choose from the available checks.",
        )
    logger.info(f"Decommissioning InfluxDB check {check_name}...")
    return await decommission_check(check_name)
