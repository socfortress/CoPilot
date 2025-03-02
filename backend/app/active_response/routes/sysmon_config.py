from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from xml.parsers.expat import ExpatError
import xml.etree.ElementTree as ET

from app.data_store.data_store_operations import upload_sysmon_config, download_sysmon_config, list_sysmon_configs
from app.db.db_session import get_db_session
from app.active_response.schema.sysmon_config import SysmonConfigContentResponse
from app.active_response.schema.sysmon_config import SysmonConfigListResponse
from app.active_response.schema.sysmon_config import SysmonConfigUploadResponse
from app.active_response.services.sysmon_config import validate_sysmon_config
from app.active_response.services.sysmon_config import check_config_exists

sysmon_config_router = APIRouter()



@sysmon_config_router.post("/upload", response_model=SysmonConfigUploadResponse)
async def upload_customer_sysmon_config(
    customer_code: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session)
):
    """Upload a sysmon config XML file for a specific customer."""
    # Validate file extension
    if not file.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="Only XML files are accepted for sysmon configs")

    try:
        # Read and validate file content
        file_content = await file.read()
        xml_content = file_content.decode('utf-8')
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
            overwritten=file_exists
        )
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 encoded text")

# This route must come before the /{customer_code} route
@sysmon_config_router.get("/content/{customer_code}", response_model=SysmonConfigContentResponse)
async def get_customer_sysmon_config_content(
    customer_code: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Get the sysmon config for a specific customer as a string."""
    try:
        data_bytes = await download_sysmon_config(customer_code)
        xml_content = data_bytes.decode('utf-8')

        return SysmonConfigContentResponse(
            success=True,
            message=f"Successfully retrieved Sysmon config",
            customer_code=customer_code,
            config_content=xml_content
        )
    except UnicodeDecodeError:
        raise HTTPException(status_code=500, detail="Failed to decode config file as UTF-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving config: {str(e)}")

@sysmon_config_router.get("/", response_model=SysmonConfigListResponse)
async def get_all_sysmon_configs(
    session: AsyncSession = Depends(get_db_session)
):
    """List all customers that have sysmon configs."""
    customers = await list_sysmon_configs()

    return SysmonConfigListResponse(
        success=True,
        message="Successfully retrieved list of customer sysmon configs",
        customer_codes=customers
    )

@sysmon_config_router.get("/{customer_code}")
async def get_customer_sysmon_config(
    customer_code: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Download the sysmon config for a specific customer."""
    try:
        data = await download_sysmon_config(customer_code)
        return Response(
            content=data,
            media_type="application/xml",
            headers={
                "Content-Disposition": f"attachment; filename=sysmon_config_{customer_code}.xml"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving config: {str(e)}")
