from enum import Enum
from typing import Any
from typing import List
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field


class AvailableInfluxDBChecks(str, Enum):
    """
    The InfluxDB checks CoPilot can provision. The enum *name* is the template file stem
    under `app/stack_provisioning/influxdb/templates/`, the value is the operator-facing
    description.
    """

    SOCFORTRESS_INFLUXDB_CPU_CHECK = (
        "Threshold check on CPU idle time (`cpu`/`usage_idle`). Raises INFO below 25% idle,"
        " WARN below 15% and CRIT below 5%, evaluated every minute per host."
    )
    SOCFORTRESS_INFLUXDB_MEMORY_CHECK = (
        "Threshold check on available memory (`mem`/`available_percent`). Raises INFO below 25%"
        " available, WARN below 15% and CRIT below 10%, evaluated every minute per host."
    )
    SOCFORTRESS_INFLUXDB_DISK_CHECK = (
        "Threshold check on filesystem usage (`disk`/`used_percent`), excluding pseudo filesystems."
        " Raises INFO above 75% used, WARN above 85% and CRIT above 90%, evaluated every 5 minutes"
        " per host and mount point."
    )
    SOCFORTRESS_INFLUXDB_CRITICAL_SERVICES_CHECK = (
        "Threshold check on the critical SIEM stack systemd units (`systemd_units`/`active_code`)."
        " Raises CRIT when a watched unit reports failed, evaluated every minute per host and unit."
        " A unit that is stopped by design is deliberately ignored, so the check is safe on a"
        " role-split stack where not every host runs every service."
    )


class InfluxDBCheck(BaseModel):
    name: str = Field(..., description="The template name of the check")
    description: str = Field(..., description="What the check does and when it fires")
    check_name: str = Field(
        ...,
        examples=["CPU CHECK"],
        description="The name the check is created with inside InfluxDB",
    )
    provisioned: bool = Field(
        ...,
        examples=[False],
        description="Whether a check with this name already exists in InfluxDB",
    )


class AvailableInfluxDBChecksResponse(BaseModel):
    available_checks: List[InfluxDBCheck] = Field(
        ...,
        description="The InfluxDB checks available for provisioning",
    )
    success: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["Available InfluxDB checks retrieved successfully"])


class ProvisionInfluxDBCheckRequest(BaseModel):
    check_name: AvailableInfluxDBChecks = Field(
        ...,
        examples=[AvailableInfluxDBChecks.SOCFORTRESS_INFLUXDB_CPU_CHECK],
        description="The name of the check to provision in InfluxDB",
    )
    overwrite: bool = Field(
        False,
        examples=[False],
        description=(
            "Overwrite the check if one with the same name already exists. Defaults to False so that"
            " hand-tuned checks on an existing stack are never silently replaced."
        ),
    )

    def __init__(self, **data: Any):
        check_name = data.get("check_name")
        try:
            data["check_name"] = AvailableInfluxDBChecks[check_name]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Check {check_name} is not available. Please choose from the available checks.",
            )
        super().__init__(**data)


class ProvisionInfluxDBAllChecksRequest(BaseModel):
    overwrite: bool = Field(
        False,
        examples=[False],
        description="Overwrite checks that already exist in InfluxDB",
    )


class ProvisionedInfluxDBCheck(BaseModel):
    name: str = Field(..., description="The template name of the check")
    check_name: str = Field(..., description="The name of the check inside InfluxDB")
    action: str = Field(
        ...,
        examples=["created"],
        description="What happened to the check: `created`, `updated` or `skipped`",
    )
    check_id: Optional[str] = Field(
        None,
        description="The InfluxDB ID of the check, absent when the check was skipped",
    )


class ProvisionInfluxDBResponse(BaseModel):
    results: List[ProvisionedInfluxDBCheck] = Field(
        default_factory=list,
        description="Per-check outcome of the provisioning run",
    )
    success: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["InfluxDB check provisioned successfully"])


class DecommissionInfluxDBCheckResponse(BaseModel):
    success: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["InfluxDB check decommissioned successfully"])
