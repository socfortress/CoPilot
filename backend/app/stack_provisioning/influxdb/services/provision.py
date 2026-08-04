import json
from pathlib import Path
from typing import Dict
from typing import List

from fastapi import HTTPException
from loguru import logger

from app.connectors.influxdb.utils.universal import get_influxdb_bucket
from app.connectors.influxdb.utils.universal import get_influxdb_org_id
from app.connectors.influxdb.utils.universal import send_delete_request
from app.connectors.influxdb.utils.universal import send_get_request
from app.connectors.influxdb.utils.universal import send_post_request
from app.connectors.influxdb.utils.universal import send_put_request
from app.stack_provisioning.influxdb.schema.provision import AvailableInfluxDBChecks
from app.stack_provisioning.influxdb.schema.provision import (
    AvailableInfluxDBChecksResponse,
)
from app.stack_provisioning.influxdb.schema.provision import (
    DecommissionInfluxDBCheckResponse,
)
from app.stack_provisioning.influxdb.schema.provision import InfluxDBCheck
from app.stack_provisioning.influxdb.schema.provision import ProvisionedInfluxDBCheck
from app.stack_provisioning.influxdb.schema.provision import (
    ProvisionInfluxDBCheckRequest,
)
from app.stack_provisioning.influxdb.schema.provision import ProvisionInfluxDBResponse

# Placeholders substituted into the check templates at provisioning time. The org ID is
# resolved from the org *name* on the connector, the bucket is the second half of
# `connector_extra_data`.
REPLACE_ORG_ID = "REPLACE_ORG_ID"
REPLACE_BUCKET = "REPLACE_BUCKET"


def get_check_template_path(file_name: str) -> Path:
    """
    Return the path to a check template JSON file.

    Args:
        file_name (str): The template file name, e.g. `SOCFORTRESS_INFLUXDB_CPU_CHECK.json`.

    Returns:
        Path: The path to the template file.
    """
    current_file = Path(__file__)  # Path to the current file
    base_dir = current_file.parent.parent  # Move up to the 'influxdb' directory
    return base_dir / "templates" / file_name


def load_raw_check_template(template_name: str) -> dict:
    """
    Load a check template straight off disk, placeholders intact.

    Used when only the metadata is needed (e.g. the InfluxDB check name for the available
    checks listing), so that listing does not have to hit the InfluxDB API to resolve the
    org ID first.

    Args:
        template_name (str): The template name, e.g. `SOCFORTRESS_INFLUXDB_CPU_CHECK`.

    Returns:
        dict: The raw template.

    Raises:
        HTTPException: If the template file is missing or is not valid JSON.
    """
    file_path = get_check_template_path(f"{template_name}.json")
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"InfluxDB check template not found at {file_path}")
        raise HTTPException(
            status_code=404,
            detail=f"InfluxDB check template {template_name} not found",
        )
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode InfluxDB check template {file_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"InfluxDB check template {template_name} is not valid JSON: {e}",
        )


async def render_check_template(template_name: str) -> dict:
    """
    Load a check template and substitute the deployment specific placeholders.

    Args:
        template_name (str): The template name, e.g. `SOCFORTRESS_INFLUXDB_CPU_CHECK`.

    Returns:
        dict: The check payload ready to be POSTed/PUT to InfluxDB.
    """
    logger.info(f"Rendering InfluxDB check template: {template_name}")
    template = load_raw_check_template(template_name)
    org_id = await get_influxdb_org_id()
    bucket = await get_influxdb_bucket()
    rendered = json.dumps(template).replace(REPLACE_ORG_ID, org_id).replace(REPLACE_BUCKET, bucket)
    return json.loads(rendered)


async def get_existing_checks() -> Dict[str, str]:
    """
    Fetch the checks that already exist in InfluxDB, keyed by name.

    Returns:
        Dict[str, str]: A mapping of check name to check ID.
    """
    response = await send_get_request("/api/v2/checks", params={"limit": 100})
    checks = (response or {}).get("checks", [])
    return {check["name"]: check["id"] for check in checks if check.get("name")}


async def get_available_checks() -> AvailableInfluxDBChecksResponse:
    """
    List the checks CoPilot can provision, flagging the ones already present in InfluxDB.

    Returns:
        AvailableInfluxDBChecksResponse: The available checks and their provisioning state.
    """
    logger.info("Getting available InfluxDB checks...")
    existing_checks = await get_existing_checks()

    available_checks: List[InfluxDBCheck] = []
    for check in AvailableInfluxDBChecks:
        template = load_raw_check_template(check.name)
        check_name = template["name"]
        available_checks.append(
            InfluxDBCheck(
                name=check.name,
                description=check.value,
                check_name=check_name,
                provisioned=check_name in existing_checks,
            ),
        )

    return AvailableInfluxDBChecksResponse(
        available_checks=available_checks,
        success=True,
        message="Available InfluxDB checks retrieved successfully",
    )


async def provision_single_check(template_name: str, overwrite: bool) -> ProvisionedInfluxDBCheck:
    """
    Create or update a single InfluxDB check from its template.

    A check that already exists is left untouched unless `overwrite` is set — SOCFortress
    stacks are frequently built by hand first, and blindly PUTting the template over an
    existing check would discard whatever tuning an engineer did in the InfluxDB UI.

    Args:
        template_name (str): The template name, e.g. `SOCFORTRESS_INFLUXDB_CPU_CHECK`.
        overwrite (bool): Whether to replace an existing check of the same name.

    Returns:
        ProvisionedInfluxDBCheck: The outcome for this check.
    """
    payload = await render_check_template(template_name)
    check_name = payload["name"]
    existing_checks = await get_existing_checks()
    existing_id = existing_checks.get(check_name)

    if existing_id and not overwrite:
        logger.info(f"InfluxDB check {check_name} already exists, skipping")
        return ProvisionedInfluxDBCheck(
            name=template_name,
            check_name=check_name,
            action="skipped",
            check_id=existing_id,
        )

    if existing_id:
        logger.info(f"Updating existing InfluxDB check {check_name} ({existing_id})")
        response = await send_put_request(f"/api/v2/checks/{existing_id}", data=payload)
        action = "updated"
    else:
        logger.info(f"Creating InfluxDB check {check_name}")
        response = await send_post_request("/api/v2/checks", data=payload)
        action = "created"

    return ProvisionedInfluxDBCheck(
        name=template_name,
        check_name=check_name,
        action=action,
        check_id=(response or {}).get("id"),
    )


async def provision_check(request: ProvisionInfluxDBCheckRequest) -> ProvisionInfluxDBResponse:
    """
    Provision a single InfluxDB check.

    Args:
        request (ProvisionInfluxDBCheckRequest): The check to provision.

    Returns:
        ProvisionInfluxDBResponse: The outcome of the provisioning run.
    """
    result = await provision_single_check(request.check_name.name, request.overwrite)
    if result.action == "skipped":
        message = f"{result.check_name} already exists in InfluxDB and was left unchanged. Set overwrite to replace it."
    else:
        message = f"{result.check_name} {result.action} successfully"
    return ProvisionInfluxDBResponse(results=[result], success=True, message=message)


async def provision_all_checks(overwrite: bool) -> ProvisionInfluxDBResponse:
    """
    Provision every available InfluxDB check.

    Args:
        overwrite (bool): Whether to replace checks that already exist.

    Returns:
        ProvisionInfluxDBResponse: The per-check outcomes of the provisioning run.
    """
    logger.info("Provisioning all InfluxDB checks...")
    results = [await provision_single_check(check.name, overwrite) for check in AvailableInfluxDBChecks]

    created = sum(1 for result in results if result.action == "created")
    updated = sum(1 for result in results if result.action == "updated")
    skipped = sum(1 for result in results if result.action == "skipped")

    return ProvisionInfluxDBResponse(
        results=results,
        success=True,
        message=f"InfluxDB checks provisioned: {created} created, {updated} updated, {skipped} skipped",
    )


async def decommission_check(template_name: str) -> DecommissionInfluxDBCheckResponse:
    """
    Delete a provisioned InfluxDB check.

    Args:
        template_name (str): The template name, e.g. `SOCFORTRESS_INFLUXDB_CPU_CHECK`.

    Returns:
        DecommissionInfluxDBCheckResponse: The outcome of the deletion.

    Raises:
        HTTPException: If the check does not exist in InfluxDB.
    """
    template = load_raw_check_template(template_name)
    check_name = template["name"]
    existing_checks = await get_existing_checks()
    existing_id = existing_checks.get(check_name)

    if not existing_id:
        raise HTTPException(
            status_code=404,
            detail=f"InfluxDB check {check_name} does not exist",
        )

    logger.info(f"Deleting InfluxDB check {check_name} ({existing_id})")
    await send_delete_request(f"/api/v2/checks/{existing_id}")
    return DecommissionInfluxDBCheckResponse(
        success=True,
        message=f"{check_name} decommissioned successfully",
    )
