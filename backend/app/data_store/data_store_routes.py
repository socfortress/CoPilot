from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from loguru import logger
from typing import Optional
import io

from app.data_store.data_store_schema import (
    AgentDataStoreResponse,
    AgentDataStoreListResponse,
    AgentDataStoreData,
)
from app.data_store.data_store_operations import (
    download_agent_artifact_file,
    list_agent_artifact_files,
    delete_agent_artifact_file,
)
from app.db.universal_models import AgentDataStore
from app.db.db_session import get_db
from app.auth.utils import AuthHandler

agent_data_store_router = APIRouter()


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
        query = select(AgentDataStore).where(
            AgentDataStore.id == artifact_id,
            AgentDataStore.agent_id == agent_id
        )
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
        result = await session.execute(
            select(AgentDataStore).where(
                AgentDataStore.id == artifact_id,
                AgentDataStore.agent_id == agent_id
            )
        )
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
        result = await session.execute(
            select(AgentDataStore).where(
                AgentDataStore.id == artifact_id,
                AgentDataStore.agent_id == agent_id
            )
        )
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
