from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from xml.parsers.expat import ExpatError
import xml.etree.ElementTree as ET

from app.data_store.data_store_operations import upload_sysmon_config, download_sysmon_config, list_sysmon_configs
from app.db.db_session import get_db_session

sysmon_config_router = APIRouter()


@sysmon_config_router.post("/upload")
async def upload_customer_sysmon_config(
    customer_code: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Upload a sysmon config XML file for a specific customer.

    The file will be stored in the customer's folder within the sysmon-configs bucket.
    If the customer folder doesn't exist, it will be created automatically.
    If a config file already exists, it will be overwritten.
    """
    # Validate file extension is XML
    if not file.filename.endswith('.xml'):
        raise HTTPException(
            status_code=400,
            detail="Only XML files are accepted for sysmon configs"
        )

    # Read file content for validation
    file_content = await file.read()

    # Validate XML syntax
    try:
        # Try parsing the XML to validate syntax
        xml_content = file_content.decode('utf-8')
        root = ET.fromstring(xml_content)

        # Optional: Verify this is actually a Sysmon config by checking for expected elements
        if root.tag != 'Sysmon' and not root.findall(".//EventFiltering"):
            raise HTTPException(
                status_code=400,
                detail="The XML file does not appear to be a valid Sysmon configuration"
            )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File is not valid UTF-8 encoded text"
        )
    except ET.ParseError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid XML syntax: {str(e)}"
        )

    # Reset file pointer for upload
    await file.seek(0)

    # Check if file already exists
    file_exists = False
    try:
        # Try to download the existing file to see if it exists
        await download_sysmon_config(customer_code)
        file_exists = True
    except HTTPException as e:
        # File doesn't exist if we get a 404
        if e.status_code != 404:
            # Re-raise for other errors
            raise

    # Upload the validated file (MinIO will overwrite by default)
    await upload_sysmon_config(customer_code, file)

    return {
        "success": True,
        "message": f"Successfully {'updated' if file_exists else 'uploaded'} Sysmon config for customer {customer_code}",
        "customer_code": customer_code,
        "filename": "sysmon_config.xml",
        "overwritten": file_exists
    }

@sysmon_config_router.get("/{customer_code}")
async def get_customer_sysmon_config(
    customer_code: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Download the sysmon config for a specific customer.
    """
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
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving sysmon config: {str(e)}"
        )

@sysmon_config_router.get("/")
async def get_all_sysmon_configs(
    session: AsyncSession = Depends(get_db_session)
):
    """
    List all customers that have sysmon configs.
    """
    customers = await list_sysmon_configs()

    return {
        "success": True,
        "message": "Successfully retrieved list of customer sysmon configs",
        "customer_codes": customers
    }

@sysmon_config_router.get("/content/{customer_code}")
async def get_customer_sysmon_config_content(
    customer_code: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get the sysmon config for a specific customer as a string.

    Returns the XML content directly for display in the frontend UI.
    """
    try:
        # Get the data as bytes
        data_bytes = await download_sysmon_config(customer_code)

        # Convert to string
        xml_content = data_bytes.decode('utf-8')

        return {
            "success": True,
            "message": f"Successfully retrieved Sysmon config for customer {customer_code}",
            "customer_code": customer_code,
            "config_content": xml_content
        }
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Failed to decode Sysmon config file as UTF-8"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving sysmon config: {str(e)}"
        )
