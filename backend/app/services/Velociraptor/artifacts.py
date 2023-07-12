from loguru import logger

from app.services.Velociraptor.universal import UniversalService


class ArtifactsService:
    """
    A service class that encapsulates the logic for pulling artifacts from Velociraptor.
    """

    def __init__(self):
        self.universal_service = UniversalService()

    def _create_query(self, query: str) -> str:
        """
        Create a query string.

        Args:
            query (str): The query to be executed.

        Returns:
            str: The created query string.
        """
        return query

    def _get_artifact_key(self, client_id: str, artifact: str) -> str:
        """
        Construct the artifact key.

        Args:
            client_id (str): The ID of the client.
            artifact (str): The name of the artifact.

        Returns:
            str: The constructed artifact key.
        """
        return f"collect_client(client_id='{client_id}', artifacts=['{artifact}'])"

    def collect_artifacts(self) -> dict:
        """
        Collect the artifacts from Velociraptor.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the artifacts.
        """
        query = self._create_query("SELECT name FROM artifact_definitions()")
        return self.universal_service.execute_query(query)

    def collect_artifacts_prefixed(self, prefix: str) -> dict:
        """
        Collect the artifacts from Velociraptor that have a name beginning with a specific prefix.

        Args:
            prefix (str): The prefix to filter the artifacts.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the artifacts.
        """
        artifacts_response = self.collect_artifacts()
        if not artifacts_response["success"]:
            return artifacts_response

        filtered_artifacts = [artifact for artifact in artifacts_response["results"] if artifact["name"].startswith(prefix)]

        return {
            "success": True,
            "message": f"Successfully collected {prefix} artifacts",
            "artifacts": filtered_artifacts,
        }

    def collect_artifacts_linux(self) -> dict:
        """
        Collect the artifacts from Velociraptor that have a name beginning with `Linux`.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the artifacts.
        """
        return self.collect_artifacts_prefixed("Linux.")

    def collect_artifacts_windows(self) -> dict:
        """
        Collect the artifacts from Velociraptor that have a name beginning with `Windows`.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the artifacts.
        """
        return self.collect_artifacts_prefixed("Windows.")

    def collect_artifacts_macos(self) -> dict:
        """
        Collect the artifacts from Velociraptor that have a name beginning with `MacOS`.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the artifacts.
        """
        return self.collect_artifacts_prefixed("MacOS.")

    def run_artifact_collection(self, client_id: str, artifact: str) -> dict:
        """
        Run an artifact collection on a specific client.

        Args:
            client_id (str): The ID of the client.
            artifact (str): The name of the artifact.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the results.
        """
        try:
            query = self._create_query(
                f"SELECT collect_client(client_id='{client_id}', artifacts=['{artifact}']) FROM scope()",
            )
            flow = self.universal_service.execute_query(query)
            logger.info(f"Successfully ran artifact collection on {flow}")

            artifact_key = self._get_artifact_key(client_id, artifact)
            flow_id = flow["results"][0][artifact_key]["flow_id"]
            logger.info(f"Successfully ran artifact collection on {flow_id}")

            completed = self.universal_service.watch_flow_completion(flow_id)
            logger.info(f"Successfully watched flow completion on {completed}")

            results = self.universal_service.read_collection_results(
                client_id,
                flow_id,
                artifact,
            )
            return results
        except Exception as err:
            logger.error(f"Failed to run artifact collection: {err}")
            return {
                "message": "Failed to run artifact collection",
                "success": False,
            }
