import json
from datetime import datetime
from typing import Any
from typing import Dict

import grpc
import pyvelociraptor
from fastapi import HTTPException
from loguru import logger
from pyvelociraptor import api_pb2
from pyvelociraptor import api_pb2_grpc

from app.connectors.utils import get_connector_info_from_db
from app.db.db_session import AsyncSessionLocal
from app.db.db_session import get_db_session


async def verify_velociraptor_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to Velociraptor service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    try:
        connector_api_key = attributes["connector_api_key"]

        with open(connector_api_key, "r") as f:
            f.read()

        try:
            config = pyvelociraptor.LoadConfigFile(connector_api_key)
            creds = grpc.ssl_channel_credentials(
                root_certificates=config["ca_certificate"].encode("utf8"),
                private_key=config["client_private_key"].encode("utf8"),
                certificate_chain=config["client_cert"].encode("utf8"),
            )

            options = (("grpc.ssl_target_name_override", "VelociraptorServer"),)

            with grpc.secure_channel(
                config["api_connection_string"],
                creds,
                options,
            ) as channel:
                stub = api_pb2_grpc.APIStub(channel)
                client_query = "SELECT * FROM info()"

                client_request = api_pb2.VQLCollectorArgs(
                    max_wait=60,
                    Query=[
                        api_pb2.VQLRequest(
                            Name="ClientQuery",
                            VQL=client_query,
                        ),
                    ],
                )

                r = []
                for response in stub.Query(client_request):
                    if response.Response:
                        r = r + json.loads(response.Response)
                return {
                    "connectionSuccessful": True,
                    "message": "Connection to Velociraptor successful",
                }
        except Exception as e:
            logger.error(f"Failed to verify connection to Velociraptor: {e}")
            return {
                "connectionSuccessful": False,
                "message": f"Failed to verify connection to Velociraptor: {e}",
            }
    except Exception as e:
        logger.error(f"Failed to get connector_api_key from the database: {e}")
        return {
            "connectionSuccessful": False,
            "message": f"Failed to get connector_api_key from the database: {e}",
        }


async def verify_velociraptor_connection(connector_name: str) -> str:
    """
    Verifies the connection to Velociraptor service.
    """
    logger.info(
        f"Verifying the Velociraptor connection for connector: {connector_name}",
    )
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        logger.error("No Velociraptor connector found in the database")
        return None
    return await verify_velociraptor_credentials(attributes)


class UniversalService:
    """
    A service class that encapsulates the logic for polling messages from Velociraptor.
    """

    # ! Modify this to use AsyncSessionLocal Begin - ALSO SEE BELOW CLASS METHOD
    def __init__(self) -> None:
        self.connector_api_key = None
        self.config = None

    async def setup_velociraptor_connector(self, connector_name: str):
        async with AsyncSessionLocal() as session:
            attributes = await get_connector_info_from_db(connector_name, session)
        if attributes is None:
            logger.error("No Velociraptor connector found in the database")
            return None
        self.connector_api_key = attributes["connector_api_key"]
        self.config = pyvelociraptor.LoadConfigFile(self.connector_api_key)

    # ! Modify this to use AsyncSessionLocal End

    async def setup_grpc_channel_and_stub(self):
        """
        Sets up the gRPC channel and stub for Velociraptor.
        """
        creds = grpc.ssl_channel_credentials(
            root_certificates=self.config["ca_certificate"].encode("utf8"),
            private_key=self.config["client_private_key"].encode("utf8"),
            certificate_chain=self.config["client_cert"].encode("utf8"),
        )
        options = (("grpc.ssl_target_name_override", "VelociraptorServer"),)
        self.channel = grpc.secure_channel(
            self.config["api_connection_string"],
            creds,
            options,
        )
        self.stub = api_pb2_grpc.APIStub(self.channel)

    # ! Modify this to use AsyncSessionLocal Begin
    @classmethod
    async def create(cls, connector_name: str):
        instance = cls()
        await instance.setup_velociraptor_connector(connector_name)
        await instance.setup_grpc_channel_and_stub()
        return instance

    # ! Modify this to use AsyncSessionLocal End

    def create_vql_request(self, vql: str, org_id: str = "root"):
        """
        Creates a VQLCollectorArgs object with given VQL query.

        Args:
            vql (str): The VQL query.

        Returns:
            VQLCollectorArgs: The VQLCollectorArgs object with given VQL query.
        """
        return api_pb2.VQLCollectorArgs(
            max_wait=1,
            org_id=org_id,
            Query=[
                api_pb2.VQLRequest(
                    Name="VQLRequest",
                    VQL=vql,
                ),
            ],
        )

    def execute_query(self, vql: str, org_id: str = "root"):
        """
        Executes a VQL query and returns the results.

        Args:
            vql (str): The VQL query to be executed.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the results.
        """
        logger.info(f"Executing query: {vql}")

        client_request = self.create_vql_request(vql, org_id)

        try:
            results = []
            for response in self.stub.Query(client_request, timeout=30):
                if response.Response:
                    results += json.loads(response.Response)
            return {
                "success": True,
                "message": "Successfully executed query",
                "results": results,
            }
        except grpc.RpcError as e:  # Catch gRPC-specific errors
            if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                logger.error("Failed to execute query due to timeout.")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to execute query due to timeout. Make sure the Velocraptor server has stopped this artifact collection.",
                )
            else:
                logger.error(f"Failed to execute query: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to execute query: {e.details()}",
                )
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to execute query: {e}")

    def watch_flow_completion(self, flow_id: str, org_id: str = "root"):
        """
        Watch for the completion of a flow.

        Args:
            flow_id (str): The ID of the flow.

        Returns:
            dict: A dictionary with the success status and a message.
        """
        vql = f"SELECT * FROM watch_monitoring(artifact='System.Flow.Completion') WHERE FlowId='{flow_id}' LIMIT 1"
        logger.info(f"Watching flow {flow_id} for completion")
        return self.execute_query(vql, org_id)

    def read_collection_results(
        self,
        client_id: str,
        flow_id: str,
        org_id: str = "root",
        artifact: str = "Generic.Client.Info/BasicInformation",
    ):
        """
        Read the results of a collection.

        Args:
            client_id (str): The client ID.
            flow_id (str): The ID of the flow.
            artifact (str, optional): The artifact. Defaults to 'Generic.Client.Info/BasicInformation'.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the results.
        """
        vql = f"SELECT * FROM source(client_id='{client_id}', flow_id='{flow_id}', artifact='{artifact}')"
        return self.execute_query(vql, org_id)

    async def get_client_id(self, client_name: str):
        """
        Get the client_id associated with a given client_name.

        Args:
            client_name (str): The asset name to search for.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the client_id.
        """
        # Formulate queries
        try:
            vql_client_id = f"select client_id,os_info from clients(search='host:{client_name}')"
            vql_last_seen_at = f"select last_seen_at from clients(search='host:{client_name}')"

            # Get the last seen timestamp
            logger.info(f"Getting last seen at timestamp for {client_name}")

            last_seen_at = await self._get_last_seen_timestamp(vql_last_seen_at)

            logger.info(f"Last seen at timestamp for {client_name}: {last_seen_at}")

            # if last_seen_at is longer than 30 seconds from now, return False
            if await self._is_offline(last_seen_at):
                return self.execute_query(vql_client_id)

            return self.execute_query(vql_client_id)
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get Client ID for {client_name}: {e}",
                "results": [{"client_id": None}],
            }

    async def get_client_id_via_client_id(self, client_id: str):
        """
        Get the client_id associated with a given client_id.

        Args:
            client_id (str): The client_id to search for.

        Returns:
            dict: A dictionary with the success status, a message, and potentially the client_id.
        """
        # Formulate queries
        try:
            vql_client_id = f"select client_id,os_info from clients(search='client_id:{client_id}')"
            vql_last_seen_at = f"select last_seen_at from clients(search='client_id:{client_id}')"

            # Get the last seen timestamp
            logger.info(f"Getting last seen at timestamp for {client_id}")

            last_seen_at = await self._get_last_seen_timestamp(vql_last_seen_at)

            logger.info(f"Last seen at timestamp for {client_id}: {last_seen_at}")

            # if last_seen_at is longer than 30 seconds from now, return False
            if await self._is_offline(last_seen_at):
                return self.execute_query(vql_client_id)

            return self.execute_query(vql_client_id)
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get Client ID for {client_id}: {e}",
                "results": [{"client_id": None}],
            }

    async def _get_last_seen_timestamp(self, vql: str):
        """
        Executes the VQL query and returns the last_seen_at timestamp.

        Args:
            vql (str): The VQL query.

        Returns:
            float: The last_seen_at timestamp.
        """
        return self.execute_query(vql)["results"][0]["last_seen_at"]

    async def _get_client_version(self, vql: str):
        """
        Executes the VQL query and returns the `agent_information``version` field

        Args:
            vql (str): The VQL query.

        Returns:
            str: The client version.
        """
        return self.execute_query(vql)["results"][0]["agent_information"]["version"]

    async def _get_server_version(self, vql: str):
        """
        Executes the VQL query and returns the velociraptor server version.

        Args:
            vql (str): The VQL query.

        Returns:
            str: The server version.
        """
        try:
            return self.execute_query(vql)["results"][0]["version"]["version"]
        except IndexError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get server version: {e}",
            )

    async def _is_offline(self, last_seen_at: float):
        """
        Determines if the client is offline based on the last_seen_at timestamp.

        Args:
            last_seen_at (float): The last_seen_at timestamp.

        Returns:
            bool: True if the client is offline, False otherwise.
        """
        return (datetime.now() - datetime.fromtimestamp(last_seen_at / 1000000)).total_seconds() > 30
