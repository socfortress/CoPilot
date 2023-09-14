from loguru import logger
from typing import Dict, Optional, Any

from app.models.agents import AgentMetadata
from app.services.Velociraptor.universal import UniversalService


class ArtifactsService:
    """
    A service class that encapsulates the logic for pulling artifacts from Velociraptor.
    """

    QUARANTINE_ARTIFACTS = {
    "linux": "Linux.Remediation.Quarantine",
    "windows": "Windows.Remediation.Quarantine",
    }

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

    def _get_artifact_key(self, client_id: str, artifact: str, command: str = None, quarantined: bool = None) -> str:
        """
        Construct the artifact key.

        Args:
            client_id (str): The ID of the client.
            artifact (str): The name of the artifact.
            command (str): The command that was run, if applicable.

        Returns:
            str: The constructed artifact key.
        """
        if command:
            return f"collect_client(client_id='{client_id}', urgent=true, artifacts=['{artifact}'], env=dict(Command='{command}'))"
        elif quarantined:
            return f'collect_client(client_id="{client_id}", artifacts=["{artifact}"], spec=dict(`{artifact}`=dict()))'
        else:
            return f"collect_client(client_id='{client_id}', artifacts=['{artifact}'])"

    def collect_artifacts(self) -> dict:
        """
        Collect the artifacts from Velociraptor.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the artifacts.
        """
        query = self._create_query("SELECT name,description FROM artifact_definitions()")
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

    def collect_artifacts_by_hostname(self, hostname: str) -> dict:
        """
        Queries the `agent_metadata` table for the `os` field for the given `hostname` and returns the artifacts for that OS.

        Args:
            hostname (str): The hostname of the client.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the artifacts.
        """
        agent_metadata = AgentMetadata.query.filter_by(hostname=hostname).first()
        if not agent_metadata:
            return {
                "success": False,
                "message": f"Agent with hostname {hostname} not found",
            }

        os = agent_metadata.os
        if "Linux" in os:
            return self.collect_artifacts_linux()
        elif "Windows" in os:
            return self.collect_artifacts_windows()
        elif "MacOS" in os:
            return self.collect_artifacts_macos()
        else:
            return {
                "success": False,
                "message": f"OS {os} not supported",
            }

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

            update_artifact_table_response = self.universal_service.update_artifact_table(
                artifact_name=artifact,
                artifact_results=results,
                hostname=client_id,
            )

            if not update_artifact_table_response["success"]:
                logger.error(f"Failed to update artifact table: {update_artifact_table_response['message']}")
                return {
                    "message": "Failed to update artifact table",
                    "success": False,
                }

            return results
        except Exception as err:
            logger.error(f"Failed to run artifact collection: {err}")
            return {
                "message": "Failed to run artifact collection",
                "success": False,
            }

    def run_remote_command(self, client_id: str, artifact: str, command: str) -> dict:
        """
        Run a remote command on a specific client.
        Accepted artifact names are `Windows.System.PowerShell`, `Windows.System.CmdShell`.

        Args:
            client_id (str): The ID of the client.
            artifact (str): The name of the artifact.
            command (str): The command to be executed.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the results.
        """
        try:
            query = self._create_query(
                f"SELECT collect_client(client_id='{client_id}', urgent=true, artifacts=['{artifact}'], env=dict(Command='{command}')) "
                "FROM scope()",
            )
            flow = self.universal_service.execute_query(query)
            logger.info(f"Successfully ran artifact collection on {flow}")

            artifact_key = self._get_artifact_key(client_id, artifact, command)
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

    def determine_artifact(self, client_os: str) -> Optional[str]:
        """
        Determine the artifact to use based on the client's operating system.

        Args:
            client_os (str): The operating system of the client.

        Returns:
            Optional[str]: The artifact to use, or None if the OS is not supported.
        """
        client_os = client_os.lower()
        return self.QUARANTINE_ARTIFACTS.get(client_os, None)

    def execute_quarantine_query(self, client_id: str, artifact: str, universal_service: Any) -> Dict:
        """
        Execute the query to quarantine a client.

        Args:
            client_id (str): The ID of the client.
            artifact (str): The artifact to use for quarantine.
            universal_service (Any): The service used to execute the query.

        Returns:
            dict: The result of the executed query.
        """
        query = f'SELECT collect_client(client_id=\"{client_id}\", artifacts=[\"{artifact}\"], spec=dict(`{artifact}`=dict())) FROM scope()'
        return universal_service.execute_query(query)

    def handle_flow(self, flow: Dict, client_id: str, artifact: str, universal_service: Any) -> str:
        """
        Handle the flow after executing the quarantine query.

        Args:
            flow (dict): The result of the executed query.
            client_id (str): The ID of the client.
            artifact (str): The artifact to use for quarantine.
            universal_service (Any): The service used to watch the flow completion.

        Returns:
            str: The flow ID that was completed.
        """
        artifact_key = self._get_artifact_key(client_id, artifact, quarantined=True)
        flow_id = flow["results"][0][artifact_key]["flow_id"]
        return universal_service.watch_flow_completion(flow_id)

    def quarantine_endpoint(self, client_id: str, client_os: str) -> Dict[str, Any]:
        """
        Quarantine an endpoint based on its client ID and operating system.

        Args:
            client_id (str): The ID of the client.
            client_os (str): The operating system of the client.

        Returns:
            dict: A dictionary with the success status and a message.
        """
        artifact = self.determine_artifact(client_os)

        if artifact is None:
            return {
                "message": f"OS {client_os} not supported",
                "success": False,
            }

        try:
            flow = self.execute_quarantine_query(client_id, artifact, self.universal_service)
            logger.info(f"Successfully ran artifact collection on {flow}")

            completed = self.handle_flow(flow, client_id, artifact, self.universal_service)
            logger.info(f"Successfully watched flow completion on {completed}")

            return {
                "message": "Successfully quarantined endpoint",
                "success": True,
            }

        except Exception as err:
            logger.error(f"Failed to quarantine endpoint: {err}")
            return {
                "message": "Failed to quarantine endpoint",
                "success": False,
            }
