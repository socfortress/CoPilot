from typing import Union

## Auth Things
from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import Security
from fastapi import UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.connectors.schema import ConnectorListResponse
from app.connectors.schema import ConnectorResponse
from app.connectors.schema import ConnectorsListResponse
from app.connectors.schema import UpdateConnector
from app.connectors.schema import VerifyConnectorResponse
from app.connectors.services import ConnectorServices
from app.db.db_session import get_db

connector_router = APIRouter()


@connector_router.get(
    "",
    response_model=ConnectorsListResponse,
    description="Fetch all available connectors",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_connectors(
    session: AsyncSession = Depends(get_db),
) -> ConnectorsListResponse:
    """
    Fetch all available connectors from the database.

    This endpoint retrieves all the connectors stored in the database and returns them
    along with a success status and message.

    Returns:
        ConnectorListResponse: A Pydantic model containing a list of connectors and additional metadata.

    Raises:
        HTTPException: An exception with a 404 status code is raised if no connectors are found.
    """
    connectors = await ConnectorServices.fetch_all_connectors(session=session)
    if connectors:
        return {
            "connectors": connectors,
            "success": True,
            "message": "Connectors fetched successfully",
        }
    else:
        raise HTTPException(status_code=404, detail="No connectors found")


@connector_router.get(
    "/{connector_id}",
    response_model=ConnectorListResponse,
    description="Fetch a specific connector",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_connector(
    connector_id: int,
    session: AsyncSession = Depends(get_db),
) -> Union[ConnectorResponse, HTTPException]:
    """
    Fetch a specific connector by its ID.

    This endpoint retrieves a connector identified by `connector_id` from the database.

    Args:
        connector_id (int): The unique identifier for the connector to fetch.

    Returns:
        ConnectorResponse: A Pydantic model representing the fetched connector.

    Raises:
        HTTPException: An exception with a 404 status code is raised if the connector is not found.
    """
    connector = await ConnectorServices.fetch_connector_by_id(
        connector_id,
        session=session,
    )
    if connector is not None:
        return {
            "connector": connector,
            "success": True,
            "message": "Connector fetched successfully",
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"No connector found for ID: {connector_id}".format(
                connector_id=connector_id,
            ),
        )


@connector_router.post(
    "/verify/{connector_id}",
    response_model=VerifyConnectorResponse,
    description="Verify a connector. Makes an API call to the connector to verify it is working.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def verify_connector(
    connector_id: int,
    session: AsyncSession = Depends(get_db),
) -> Union[VerifyConnectorResponse, HTTPException]:
    """
    Verify a connector by its ID.

    This endpoint verifies a connector identified by `connector_id` by making an API call to the connector.

    Args:
        connector_id (int): The unique identifier for the connector to verify.

    Returns:
        ConnectorResponse: A Pydantic model representing the verified connector.

    Raises:
        HTTPException: An exception with a 404 status code is raised if the connector is not found.
    """
    connector = await ConnectorServices.verify_connector_by_id(
        connector_id,
        session=session,
    )
    if connector is None:
        raise HTTPException(
            status_code=404,
            detail=f"No connector found for ID: {connector_id}".format(
                connector_id=connector_id,
            ),
        )
    if connector["connectionSuccessful"] is False:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify connector: {connector['message']}",
        )
    return connector


@connector_router.put(
    "/{connector_id}",
    response_model=ConnectorListResponse,
    description="Update a connector",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def update_connector(
    connector_id: int,
    connector: UpdateConnector,
    session: AsyncSession = Depends(get_db),
) -> ConnectorListResponse:
    """
    Update a connector by its ID.

    This endpoint updates a connector identified by `connector_id` in the database.

    Args:
        connector_id (int): The unique identifier for the connector to update.
        connector (ConnectorListResponse): The updated connector data.

    Returns:
        ConnectorListResponse: A Pydantic model representing the updated connector.

    Raises:
        HTTPException: An exception with a 404 status code is raised if the connector is not found.
    """
    updated_connector = await ConnectorServices.update_connector_by_id(
        connector_id,
        connector,
        session=session,
    )
    if updated_connector is not None:
        await ConnectorServices.verify_connector_by_id(connector_id, session=session)
        return {
            "connector": updated_connector,
            "success": True,
            "message": "Connector updated successfully",
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"No connector found for ID: {connector_id}".format(
                connector_id=connector_id,
            ),
        )


# @connector_router.post(
#     "/upload/{connector_id}",
#     description="Upload a YAML file for a specific connector",
#     dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
# )
# async def upload_yaml_file(
#     connector_id: int,
#     file: UploadFile = File(...),
#     session: AsyncSession = Depends(get_db),
# ) -> dict:
#     """
#     Upload a YAML file for a specific connector ID.

#     This endpoint allows you to upload a `.yaml` file for a specific connector
#     identified by `connector_id`.

#     Args:
#         connector_id (int): The unique identifier for the connector.
#         file (UploadFile): The `.yaml` file to be uploaded.

#     Returns:
#         dict: A dictionary with a success message and other information.

#     Raises:
#         HTTPException: An exception with a 400 status code is raised if the file format is incorrect or connector ID is not 6.
#     """
#     if connector_id not in [5, 6]:
#         raise HTTPException(
#             status_code=400,
#             detail="Only the Velociraptor or another specific connector is allowed for YAML file uploads.",
#         )
#     if not file.filename.endswith(".yaml"):
#         raise HTTPException(status_code=400, detail="Only .yaml files are allowed.")
#     try:
#         save_file_result = await ConnectorServices.save_file(file, connector_id, session=session)
#         if save_file_result:
#             await ConnectorServices.verify_connector_by_id(
#                 connector_id,
#                 session=session,
#             )
#             return {"success": True, "message": "File uploaded successfully"}
#         else:
#             raise HTTPException(status_code=500, detail="Failed to upload file")
#     except Exception as e:
#         logger.error(f"Failed to upload file: {e}")
#         raise HTTPException(status_code=500, detail="Failed to upload file")


@connector_router.post(
    "/upload/{connector_identifier}",
    description="Upload a YAML file for a specific connector",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def upload_yaml_file(
    connector_identifier: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Upload a YAML file for a specific connector identified by ID or name.

    This endpoint allows you to upload a `.yaml` file for a connector
    identified by either its ID (number) or name (string).

    Args:
        connector_identifier (str): The unique identifier (ID or name) for the connector.
        file (UploadFile): The `.yaml` file to be uploaded.

    Returns:
        dict: A dictionary with a success message and other information.

    Raises:
        HTTPException: An exception is raised if the file format is incorrect or connector is not found/supported.
    """
    # Try to parse as integer for connector_id
    connector_id = None
    try:
        connector_id = int(connector_identifier)
        # Check if this is a valid connector ID for YAML uploads
        if connector_id not in [5, 6]:
            raise HTTPException(
                status_code=400,
                detail="Only the Velociraptor or another specific connector is allowed for YAML file uploads.",
            )
    except ValueError:
        # If not an integer, treat as connector name
        connector_name = connector_identifier
        logger.info(f"Using connector name: {connector_name}")
        try:
            # Look up the connector ID from the name
            connector = await ConnectorServices.fetch_connector_by_name(connector_name, session=session)
            if not connector:
                raise HTTPException(
                    status_code=404,
                    detail=f"No connector found with name: {connector_name}",
                )

            # Access as an attribute using dot notation, not as a dictionary
            connector_id = connector.id

            # Check if this is a valid connector for YAML uploads
            if connector_id not in [5, 6]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Connector '{connector_name}' does not support YAML file uploads.",
                )
        except Exception as e:
            logger.error(f"Error finding connector by name: {str(e)}")
            raise HTTPException(
                status_code=404,
                detail=f"Could not find connector with name: {connector_name}",
            )

    # Check file format
    if not file.filename.endswith(".yaml"):
        raise HTTPException(status_code=400, detail="Only .yaml files are allowed.")

    # Process the file upload
    try:
        save_file_result = await ConnectorServices.save_file(file, connector_id, session=session)
        if save_file_result:
            await ConnectorServices.verify_connector_by_id(
                connector_id,
                session=session,
            )
            return {"success": True, "message": "File uploaded successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to upload file")
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")
