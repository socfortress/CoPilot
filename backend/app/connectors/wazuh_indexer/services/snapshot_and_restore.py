from typing import List

from loguru import logger

from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotRepository
from app.connectors.wazuh_indexer.schema.snapshot_and_restore import SnapshotRepositoryListResponse
from app.connectors.wazuh_indexer.utils.universal import create_wazuh_indexer_client


async def list_snapshot_repositories() -> SnapshotRepositoryListResponse:
    """
    List all snapshot repositories configured in the Wazuh Indexer (OpenSearch).

    Returns:
        SnapshotRepositoryListResponse: Response containing list of repositories.
    """
    logger.info("Fetching snapshot repositories from Wazuh Indexer")

    try:
        es_client = await create_wazuh_indexer_client("Wazuh-Indexer")

        # Get all snapshot repositories using the _snapshot API
        response = es_client.snapshot.get_repository()

        repositories: List[SnapshotRepository] = []

        for repo_name, repo_data in response.items():
            repository = SnapshotRepository(
                name=repo_name,
                type=repo_data.get("type", "unknown"),
                settings=repo_data.get("settings", {}),
            )
            repositories.append(repository)

        logger.info(f"Successfully retrieved {len(repositories)} snapshot repositories")

        return SnapshotRepositoryListResponse(
            repositories=repositories,
            success=True,
            message=f"Successfully retrieved {len(repositories)} snapshot repositories",
        )

    except Exception as e:
        logger.error(f"Failed to list snapshot repositories: {e}")
        return SnapshotRepositoryListResponse(
            repositories=[],
            success=False,
            message=f"Failed to list snapshot repositories: {str(e)}",
        )
