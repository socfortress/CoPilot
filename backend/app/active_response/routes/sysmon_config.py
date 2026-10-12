from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import Security
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.active_response.schema.sysmon_config import SysmonConfigContentResponse
from app.active_response.schema.sysmon_config import SysmonConfigDeploymentResult
from app.active_response.schema.sysmon_config import SysmonConfigListResponse
from app.active_response.schema.sysmon_config import SysmonConfigUploadResponse
from app.active_response.services.sysmon_config import check_config_exists
from app.active_response.services.sysmon_config import deploy_sysmon_config_to_worker
from app.active_response.services.sysmon_config import validate_sysmon_config
from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.auth.routes.auth import AuthHandler
from app.data_store.data_store_operations import download_sysmon_config
from app.data_store.data_store_operations import list_sysmon_configs
from app.data_store.data_store_operations import upload_sysmon_config
from app.db.db_session import get_db
from app.middleware.customer_access import scoped_customer_codes
from app.middleware.customer_access import verify_customer_code_access

sysmon_config_router = APIRouter()

# Uploading a customer's config stays admin; a responder may read the configs of their
# customers and deploy them (#1219).


@sysmon_config_router.post(
    "/upload",
    response_model=SysmonConfigUploadResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def upload_customer_sysmon_config(
    customer_code: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    """Upload a sysmon config XML file for a specific customer."""
    # Validate file extension
    if not file.filename.endswith(".xml"):
        raise HTTPException(status_code=400, detail="Only XML files are accepted for sysmon configs")

    try:
        # Read and validate file content
        file_content = await file.read()
        xml_content = file_content.decode("utf-8")
        await validate_sysmon_config(xml_content)

        # Reset file pointer for upload
        await file.seek(0)

        # Check if file exists already
        file_exists = await check_config_exists(customer_code)

        # Upload file
        await upload_sysmon_config(customer_code, file)

        return SysmonConfigUploadResponse(
            success=True,
            message=f"Successfully {'updated' if file_exists else 'uploaded'} Sysmon config",
            customer_code=customer_code,
            filename="sysmon_config.xml",
            overwritten=file_exists,
        )
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 encoded text")


# This route must come before the /{customer_code} route
@sysmon_config_router.get(
    "/content/{customer_code}",
    response_model=SysmonConfigContentResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "responder")), Depends(verify_customer_code_access)],
)
async def get_customer_sysmon_config_content(customer_code: str, session: AsyncSession = Depends(get_db)):
    """Get the sysmon config for a specific customer as a string."""
    try:
        data_bytes = await download_sysmon_config(customer_code)
        xml_content = data_bytes.decode("utf-8")

        return SysmonConfigContentResponse(
            success=True,
            message="Successfully retrieved Sysmon config",
            customer_code=customer_code,
            config_content=xml_content,
        )
    except UnicodeDecodeError:
        raise HTTPException(status_code=500, detail="Failed to decode config file as UTF-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving config: {str(e)}")


@sysmon_config_router.get(
    "",
    response_model=SysmonConfigListResponse,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "responder"))],
)
async def get_all_sysmon_configs(
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List the customers that have sysmon configs, among those the caller may see."""
    customers = await list_sysmon_configs()
    allowed = await scoped_customer_codes(current_user, None, session)
    if allowed is not None:
        customers = [code for code in customers if code in allowed]

    return SysmonConfigListResponse(
        success=True,
        message="Successfully retrieved list of customer sysmon configs",
        customer_codes=customers,
    )


@sysmon_config_router.get(
    "/{customer_code}",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "responder")), Depends(verify_customer_code_access)],
)
async def get_customer_sysmon_config(customer_code: str, session: AsyncSession = Depends(get_db)):
    """Download the sysmon config for a specific customer."""
    try:
        data = await download_sysmon_config(customer_code)
        return Response(
            content=data,
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=sysmon_config_{customer_code}.xml"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving config: {str(e)}")


@sysmon_config_router.post(
    "/deploy/{customer_code}",
    response_model=SysmonConfigDeploymentResult,
    dependencies=[Security(AuthHandler().require_any_scope("admin", "responder")), Depends(verify_customer_code_access)],
)
async def deploy_sysmon_config(
    customer_code: str,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Deploy a customer's Sysmon config to the Wazuh master.
    Fetches the config from MinIO storage and sends it to the Wazuh master.
    The Wazuh Master needs to be running the Customer-Provisioning-Worker application.
    Currently we are invoking this via a wodle command that must be placed in the wazuh agent group.
    <wodle name="command">
                <disabled>no</disabled>
                <tag>sysmon-reload</tag>
                <command>"C:\Program Files (x86)\ossec-agent\active-response\bin\run_sysmon_config_reload.cmd"</command>
                <interval>24h</interval>
                <ignore_output>yes</ignore_output>
                <run_on_start>yes</run_on_start>
                <timeout>0</timeout>
        </wodle>
    Might revisit in the future to use the Wazuh API directly to invoke the active response.
    The current limitation with the active-response is that we have to wait for the manager to pass the new sysmon_config.xml
    file to the agent.
    I.E:
    {
    "endpoint": "/active-response",
    "arguments": [],
    "command": "sysmon_config_reload",
    "custom": true,
    "alert": {
        "action": "sysmon_config_reload"
    },
    "params": {
        "wait_for_complete": true,
        "agents_list": ["085"]
    }
    }
    """
    await record_audit_event(
        action=AuditAction.SYSMON_CONFIG_DEPLOY,
        actor_user_id=current_user.id,
        actor_username=current_user.username,
        customer_code=customer_code,
        entity_type="sysmon_config",
        entity_id=customer_code,
        request=request,
    )
    return await deploy_sysmon_config_to_worker(customer_code=customer_code, session=session)
