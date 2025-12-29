import io
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.utils import AuthHandler
from app.data_store.data_store_operations import delete_agent_artifact_file
from app.data_store.data_store_operations import download_agent_artifact_file
from app.data_store.data_store_operations import upload_file_to_datastore
from app.data_store.data_store_schema import AgentDataStoreData
from app.data_store.data_store_schema import AgentDataStoreListResponse
from app.data_store.data_store_schema import AgentDataStoreResponse
from app.data_store.data_store_schema import FileUploadResponse
from app.db.db_session import get_db
from app.db.universal_models import AgentDataStore

agent_data_store_router = APIRouter()


@agent_data_store_router.post(
    "/upload",
    response_model=FileUploadResponse,
    description="Upload a file to the data store",
)
async def upload_file(
    file: UploadFile = File(...),
    bucket_name: str = Form(...),
    object_name: str = Form(...),
) -> FileUploadResponse:
    """
    Upload a file to the specified bucket and object path in the data store.

    Args:
        file: The file to upload
        bucket_name: The name of the bucket to upload to
        object_name: The object path/name within the bucket (e.g., "folder/subfolder/file.txt")

    Returns:
        FileUploadResponse with upload details
    """
    try:
        logger.info(f"Uploading file {file.filename} to bucket {bucket_name} as {object_name}")

        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File name is required",
            )

        # Upload the file to MinIO
        upload_result = await upload_file_to_datastore(
            file=file,
            bucket_name=bucket_name,
            object_name=object_name,
        )

        return FileUploadResponse(
            success=True,
            message=f"File {file.filename} uploaded successfully",
            bucket_name=upload_result["bucket_name"],
            object_key=upload_result["object_key"],
            file_name=upload_result["file_name"],
            file_size=upload_result["file_size"],
            file_hash=upload_result["file_hash"],
            content_type=upload_result.get("content_type"),
        )

    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )


@agent_data_store_router.get(
    "/agent/{agent_id}/artifacts",
    response_model=AgentDataStoreListResponse,
    description="List all artifact files for an agent",
    dependencies=[Depends(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def list_agent_artifacts(
    agent_id: str,
    flow_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
) -> AgentDataStoreListResponse:
    """
    List all artifact collection files for a specific agent.
    Optionally filter by flow_id.
    """
    try:
        query = select(AgentDataStore).where(AgentDataStore.agent_id == agent_id)
        query = query.options(selectinload(AgentDataStore.agent))  # Eager load agent

        if flow_id:
            query = query.where(AgentDataStore.flow_id == flow_id)

        query = query.order_by(desc(AgentDataStore.collection_time))

        result = await session.execute(query)
        artifacts = result.scalars().all()

        # Convert to response data, accessing customer_code via relationship
        artifact_data = []
        for artifact in artifacts:
            # Create a dict from the artifact
            artifact_dict = {
                "id": artifact.id,
                "agent_id": artifact.agent_id,
                "velociraptor_id": artifact.velociraptor_id,
                "customer_code": artifact.agent.customer_code if artifact.agent else None,
                "artifact_name": artifact.artifact_name,
                "flow_id": artifact.flow_id,
                "bucket_name": artifact.bucket_name,
                "object_key": artifact.object_key,
                "file_name": artifact.file_name,
                "content_type": artifact.content_type,
                "file_size": artifact.file_size,
                "file_hash": artifact.file_hash,
                "collection_time": artifact.collection_time,
                "uploaded_by": artifact.uploaded_by,
                "notes": artifact.notes,
                "status": artifact.status,
            }
            artifact_data.append(AgentDataStoreData(**artifact_dict))

        return AgentDataStoreListResponse(
            success=True,
            message=f"Found {len(artifact_data)} artifacts for agent {agent_id}",
            data=artifact_data,
            total=len(artifact_data),
        )

    except Exception as e:
        logger.error(f"Failed to list agent artifacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agent artifacts: {str(e)}",
        )


@agent_data_store_router.get(
    "/agent/{agent_id}/artifacts/{artifact_id}",
    response_model=AgentDataStoreResponse,
    description="Get details of a specific artifact file",
    dependencies=[Depends(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_artifact_details(
    agent_id: str,
    artifact_id: int,
    session: AsyncSession = Depends(get_db),
) -> AgentDataStoreResponse:
    """Get details of a specific artifact collection file."""
    try:
        query = select(AgentDataStore).where(AgentDataStore.id == artifact_id, AgentDataStore.agent_id == agent_id)
        query = query.options(selectinload(AgentDataStore.agent))

        result = await session.execute(query)
        artifact = result.scalars().first()

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact {artifact_id} not found for agent {agent_id}",
            )

        # Create response data with customer_code from relationship
        artifact_dict = {
            "id": artifact.id,
            "agent_id": artifact.agent_id,
            "velociraptor_id": artifact.velociraptor_id,
            "customer_code": artifact.agent.customer_code if artifact.agent else None,
            "artifact_name": artifact.artifact_name,
            "flow_id": artifact.flow_id,
            "bucket_name": artifact.bucket_name,
            "object_key": artifact.object_key,
            "file_name": artifact.file_name,
            "content_type": artifact.content_type,
            "file_size": artifact.file_size,
            "file_hash": artifact.file_hash,
            "collection_time": artifact.collection_time,
            "uploaded_by": artifact.uploaded_by,
            "notes": artifact.notes,
            "status": artifact.status,
        }

        return AgentDataStoreResponse(
            success=True,
            message="Artifact details retrieved successfully",
            data=AgentDataStoreData(**artifact_dict),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get artifact details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get artifact details: {str(e)}",
        )


@agent_data_store_router.get(
    "/agent/{agent_id}/artifacts/{artifact_id}/download",
    description="Download an artifact file",
    dependencies=[Depends(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def download_agent_artifact(
    agent_id: str,
    artifact_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Download a specific artifact collection file."""
    try:
        result = await session.execute(select(AgentDataStore).where(AgentDataStore.id == artifact_id, AgentDataStore.agent_id == agent_id))
        artifact = result.scalars().first()

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact {artifact_id} not found for agent {agent_id}",
            )

        # Download from MinIO
        file_data = await download_agent_artifact_file(
            agent_id=agent_id,
            flow_id=artifact.flow_id,
            file_name=artifact.file_name,
        )

        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=artifact.content_type,
            headers={
                "Content-Disposition": f"attachment; filename={artifact.file_name}",
                "Content-Length": str(artifact.file_size),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download artifact: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download artifact: {str(e)}",
        )


@agent_data_store_router.delete(
    "/agent/{agent_id}/artifacts/{artifact_id}",
    description="Delete an artifact file",
    dependencies=[Depends(AuthHandler().require_any_scope("admin"))],
)
async def delete_agent_artifact(
    agent_id: str,
    artifact_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Delete a specific artifact collection file."""
    try:
        result = await session.execute(select(AgentDataStore).where(AgentDataStore.id == artifact_id, AgentDataStore.agent_id == agent_id))
        artifact = result.scalars().first()

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact {artifact_id} not found for agent {agent_id}",
            )

        # Delete from MinIO
        await delete_agent_artifact_file(
            agent_id=agent_id,
            flow_id=artifact.flow_id,
            file_name=artifact.file_name,
        )

        # Delete from database
        await session.delete(artifact)
        await session.commit()

        logger.info(f"Deleted artifact {artifact_id} for agent {agent_id}")

        return {
            "success": True,
            "message": f"Artifact {artifact_id} deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete artifact: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete artifact: {str(e)}",
        )
