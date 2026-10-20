import json
import os
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import anyio
import anyio.to_thread
import grpc
import pyvelociraptor
from fastapi import HTTPException
from loguru import logger
from pyvelociraptor import api_pb2
from pyvelociraptor import api_pb2_grpc

from app.blocking import run_blocking
from app.connectors.utils import get_connector_info_from_db
from app.connectors.velociraptor.utils.validation import encode_vql_value
from app.connectors.velociraptor.utils.validation import validate_artifact_name
from app.connectors.velociraptor.utils.validation import validate_client_id
from app.connectors.velociraptor.utils.validation import validate_flow_id
from app.connectors.velociraptor.utils.validation import validate_hostname
from app.connectors.velociraptor.utils.validation import validate_org_id
from app.connectors.velociraptor.utils.validation import validate_vql_variable_name
from app.db.db_session import AsyncSessionLocal
from app.db.db_session import get_db_session


def _positive_int_from_env(name: str, default: int) -> int:
    """Read a positive integer setting from the environment, falling back to `default`."""
    raw = os.getenv(name, str(default))
    try:
        parsed = int(raw)
    except ValueError:
        logger.warning(f"{name}={raw!r} is not an integer; falling back to {default}")
        return default
    if parsed <= 0:
        logger.warning(f"{name}={parsed} is not a positive integer; falling back to {default}")
        return default
    return parsed


# Ordinary VQL — listing clients, resolving a client_id, reading collection results.
# These talk to the Velociraptor server's own datastore and should answer quickly; a
# slow one means the server is unwell, and waiting minutes on it just moves the failure.
QUERY_TIMEOUT_SECONDS = _positive_int_from_env("VELOCIRAPTOR_QUERY_TIMEOUT", 30)

# Waiting for a *flow* to finish is a different kind of wait: the deadline has to cover
# however long the endpoint takes to run the artifact, which for anything touching disk
# is routinely minutes rather than seconds. Sharing the 30s query deadline meant a
# perfectly healthy collection failed with DEADLINE_EXCEEDED while it was still running
# (the flow completed server-side; only CoPilot gave up), which is what this splits.
FLOW_TIMEOUT_SECONDS = _positive_int_from_env("VELOCIRAPTOR_FLOW_TIMEOUT", 300)

# pyvelociraptor is synchronous gRPC: every call blocks the thread it runs on until
# Velociraptor answers. Run on the event loop, that thread is the whole backend, so
# one command waiting minutes for an endpoint froze every other request and the
# reverse proxy answered them with 504s (#1226). Every gRPC call therefore goes
# through `run_blocking`; the `*_async` methods below are the API for coroutines,
# and the sync methods remain only for code that is already on a worker thread.
#
# Waiting for a flow holds a worker thread for as long as the endpoint takes, up to
# FLOW_TIMEOUT_SECONDS. Those threads come from the pool every connector shares
# (`app.blocking.DEFAULT_THREAD_LIMIT`), so a burst of slow collections -- the AI
# analyst investigating several alerts at once -- could still exhaust it and stall
# every other connector call. Flow waits get their own, smaller allowance: past it
# they queue behind each other rather than starving everything else.
FLOW_WAIT_CONCURRENCY = _positive_int_from_env("VELOCIRAPTOR_MAX_CONCURRENT_FLOW_WAITS", 20)
_flow_wait_limiter = anyio.CapacityLimiter(FLOW_WAIT_CONCURRENCY)

# Client lookups by a clients() search term ("host:<name>", "client_id:<id>"), passed as the
# `Search` query variable.
VQL_CLIENT_ID_BY_SEARCH = "select client_id,os_info from clients(search=Search)"
VQL_CLIENT_LAST_SEEN_BY_SEARCH = "select last_seen_at from clients(search=Search)"
VQL_CLIENT_BY_SEARCH = "select * from clients(search=Search)"


def build_vql_env(env: Optional[Dict[str, str]]) -> List[api_pb2.VQLEnv]:
    """Turn ``{name: value}`` into the ``VQLCollectorArgs.env`` entries of a query.

    Velociraptor's Query API sets each entry as a variable in the query's scope (api/query.go),
    so the VQL references the value by name -- ``client_id=ClientId`` -- and the value is never
    part of the query text. That is what makes a quote, backslash, backtick or newline in a
    command, glob or parameter value inert (GHSA-5542-j2fc-gqjm).
    """
    entries = []
    for name, value in (env or {}).items():
        validate_vql_variable_name(name)
        if not isinstance(value, str):
            raise TypeError(f"VQL variable {name} must be a str, got {type(value).__name__}")
        encode_vql_value(value)  # protobuf string fields must be valid UTF-8
        entries.append(api_pb2.VQLEnv(key=name, value=value))
    return entries


def _verify_velociraptor_credentials_sync(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """Blocking body of `verify_velociraptor_credentials`; runs on a worker thread."""
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
                # Without a deadline an unreachable server held this check (and its
                # worker thread) for as long as gRPC kept retrying the connection.
                for response in stub.Query(client_request, timeout=QUERY_TIMEOUT_SECONDS):
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


async def verify_velociraptor_credentials(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verifies the connection to Velociraptor service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    return await run_blocking(_verify_velociraptor_credentials_sync, attributes)


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

    def create_vql_request(self, vql: str, org_id: str = "root", env: Optional[Dict[str, str]] = None):
        """
        Creates a VQLCollectorArgs object with given VQL query.

        Args:
            vql (str): The VQL query. A constant template: values belong in `env`.
            org_id (str): The Velociraptor org to run against.
            env (dict, optional): Query variables, ``{name: value}``, referenced by name in `vql`.

        Returns:
            VQLCollectorArgs: The VQLCollectorArgs object with given VQL query.
        """
        # Central choke point for every executed VQL: org_id reaches the API verbatim and is
        # also interpolated into VQL by callers, so reject any non-identifier value here
        # (GHSA-5542-j2fc-gqjm). Coalesce a falsy org to the default "root" first so callers
        # that pass None/"" keep working (and protobuf never receives None).
        org_id = org_id or "root"
        validate_org_id(org_id)
        return api_pb2.VQLCollectorArgs(
            max_wait=1,
            org_id=org_id,
            env=build_vql_env(env),
            Query=[
                api_pb2.VQLRequest(
                    Name="VQLRequest",
                    VQL=vql,
                ),
            ],
        )

    def execute_query(self, vql: str, org_id: str = "root", timeout: int = None, env: Optional[Dict[str, str]] = None):
        """
        Executes a VQL query and returns the results.

        Args:
            vql (str): The VQL query to be executed. Never interpolate a value into it:
                pass the value in `env` and reference it by name.
            org_id (str): The Velociraptor org to run against.
            timeout (int, optional): gRPC deadline in seconds. Defaults to
                `QUERY_TIMEOUT_SECONDS`; callers that wait on a flow pass
                `FLOW_TIMEOUT_SECONDS` instead.
            env (dict, optional): Query variables, ``{name: value}`` (see `build_vql_env`).

        Returns:
            dict: A dictionary with the success status, a message, and potentially the results.
        """
        timeout = timeout or QUERY_TIMEOUT_SECONDS
        # Variable names only: values can be a whole command or script, and are logged by
        # the callers that want them.
        logger.info(f"Executing query: {vql} (variables {sorted(env or {})}, timeout {timeout}s)")

        client_request = self.create_vql_request(vql, org_id, env)

        try:
            results = []
            for response in self.stub.Query(client_request, timeout=timeout):
                if response.Response:
                    results += json.loads(response.Response)
                elif response.log:
                    logger.info(f"Log: {response.log}")

            return {
                "success": True,
                "message": "Successfully executed query",
                "results": results,
            }
        except grpc.RpcError as e:  # Catch gRPC-specific errors
            if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                # Name the deadline that was hit and the knob that raises it: the flow
                # itself usually finished on the server, and the operator's next question
                # is always "how do I give it longer?".
                env_var = "VELOCIRAPTOR_FLOW_TIMEOUT" if timeout == FLOW_TIMEOUT_SECONDS else "VELOCIRAPTOR_QUERY_TIMEOUT"
                logger.error(f"Failed to execute query: deadline of {timeout}s exceeded.")
                raise HTTPException(
                    status_code=504,
                    detail=(
                        f"Velociraptor did not respond within {timeout}s. The collection may still be "
                        f"running on the server -- check the flow there before re-running it. "
                        f"Raise {env_var} (seconds) if collections on this deployment legitimately take longer."
                    ),
                )
            else:
                logger.error(f"Failed to execute query: {e}")
                details = e.details() or ""
                # A root administrator is NOT implicitly an administrator in child orgs, so an
                # org-scoped query fails with "Permission denied: ... requires permission
                # ANY_QUERY" while org enumeration (which runs at root) succeeds. That reads as a
                # CoPilot fault unless we say what the operator has to grant (GitHub issue #1015).
                if "permission denied" in details.lower():
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            f"Velociraptor denied the query for org '{org_id}': {details}. "
                            "The Velociraptor API user CoPilot authenticates as needs a role in "
                            "each org, not just root. Grant it on the Velociraptor server with: "
                            f"SELECT user_grant(user='<copilot api user>', roles='administrator', orgs=['{org_id}']) FROM scope()"
                        ),
                    )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to execute query: {details}",
                )
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to execute query: {e}")

    def watch_flow_completion(self, flow_id: str, org_id: str = "root", timeout: int = None):
        """
        Watch for the completion of a flow.

        Args:
            flow_id (str): The ID of the flow.
            org_id (str): The Velociraptor org the flow belongs to.
            timeout (int, optional): gRPC deadline in seconds. Defaults to
                `FLOW_TIMEOUT_SECONDS` -- this call blocks for as long as the endpoint
                takes to run the artifact, not for as long as the server takes to answer.

        Returns:
            dict: A dictionary with the success status and a message.
        """
        validate_flow_id(flow_id)
        vql = "SELECT * FROM watch_monitoring(artifact='System.Flow.Completion') WHERE FlowId = TargetFlowId LIMIT 1"
        logger.info(f"Watching flow {flow_id} for completion (timeout {timeout or FLOW_TIMEOUT_SECONDS}s)")
        return self.execute_query(vql, org_id, timeout=timeout or FLOW_TIMEOUT_SECONDS, env={"TargetFlowId": flow_id})

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
        validate_client_id(client_id)
        validate_flow_id(flow_id)
        validate_artifact_name(artifact)
        vql = "SELECT * FROM source(client_id=ClientId, flow_id=FlowId, artifact=ArtifactName)"
        return self.execute_query(vql, org_id, env={"ClientId": client_id, "FlowId": flow_id, "ArtifactName": artifact})

    async def execute_query_async(self, vql: str, org_id: str = "root", timeout: int = None, env: Optional[Dict[str, str]] = None):
        """`execute_query` on a worker thread, so the event loop keeps serving other requests."""
        return await run_blocking(self.execute_query, vql, org_id, timeout, env)

    async def watch_flow_completion_async(self, flow_id: str, org_id: str = "root", timeout: int = None):
        """`watch_flow_completion` on a worker thread from the flow-wait allowance.

        The gRPC deadline starts when a thread picks the wait up, so a wait queued
        behind FLOW_WAIT_CONCURRENCY others is not cut short by its time in the queue.
        """
        return await anyio.to_thread.run_sync(
            lambda: self.watch_flow_completion(flow_id, org_id, timeout),
            limiter=_flow_wait_limiter,
        )

    async def read_collection_results_async(
        self,
        client_id: str,
        flow_id: str,
        org_id: str = "root",
        artifact: str = "Generic.Client.Info/BasicInformation",
    ):
        """`read_collection_results` on a worker thread."""
        return await run_blocking(self.read_collection_results, client_id, flow_id, org_id, artifact)

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
            validate_hostname(client_name)
            env = {"Search": f"host:{client_name}"}

            # Get the last seen timestamp
            logger.info(f"Getting last seen at timestamp for {client_name}")

            last_seen_at = await self._get_last_seen_timestamp(VQL_CLIENT_LAST_SEEN_BY_SEARCH, env)

            logger.info(f"Last seen at timestamp for {client_name}: {last_seen_at}")

            # if last_seen_at is longer than 30 seconds from now, return False
            if await self._is_offline(last_seen_at):
                return await self.execute_query_async(VQL_CLIENT_ID_BY_SEARCH, env=env)

            return await self.execute_query_async(VQL_CLIENT_ID_BY_SEARCH, env=env)
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
            env = {"Search": f"client_id:{client_id}"}

            # Get the last seen timestamp
            logger.info(f"Getting last seen at timestamp for {client_id}")

            last_seen_at = await self._get_last_seen_timestamp(VQL_CLIENT_LAST_SEEN_BY_SEARCH, env)

            logger.info(f"Last seen at timestamp for {client_id}: {last_seen_at}")

            # if last_seen_at is longer than 30 seconds from now, return False
            if await self._is_offline(last_seen_at):
                return await self.execute_query_async(VQL_CLIENT_ID_BY_SEARCH, env=env)

            return await self.execute_query_async(VQL_CLIENT_ID_BY_SEARCH, env=env)
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get Client ID for {client_id}: {e}",
                "results": [{"client_id": None}],
            }

    async def _get_last_seen_timestamp(self, vql: str, env: Optional[Dict[str, str]] = None):
        """
        Executes the VQL query and returns the last_seen_at timestamp.

        Args:
            vql (str): The VQL query.
            env (dict, optional): Query variables referenced by `vql`.

        Returns:
            float: The last_seen_at timestamp.
        """
        return (await self.execute_query_async(vql, env=env))["results"][0]["last_seen_at"]

    async def _get_client_version(self, vql: str, env: Optional[Dict[str, str]] = None):
        """
        Executes the VQL query and returns the `agent_information``version` field

        Args:
            vql (str): The VQL query.
            env (dict, optional): Query variables referenced by `vql`.

        Returns:
            str: The client version.
        """
        return (await self.execute_query_async(vql, env=env))["results"][0]["agent_information"]["version"]

    async def _get_server_version(self, vql: str):
        """
        Executes the VQL query and returns the velociraptor server version.

        Args:
            vql (str): The VQL query.

        Returns:
            str: The server version.
        """
        try:
            return (await self.execute_query_async(vql))["results"][0]["version"]["version"]
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
