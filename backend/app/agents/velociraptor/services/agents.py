from datetime import datetime

from fastapi import HTTPException
from loguru import logger

from app.agents.schema.agents import AgentModifyResponse
from app.agents.velociraptor.schema.agents import VelociraptorAgent
from app.connectors.velociraptor.utils.universal import UniversalService


def create_query(query: str) -> str:
    """
    Create a query string.

    Args:
        query (str): The query to be executed.

    Returns:
        str: The created query string.
    """
    return query


async def collect_velociraptor_clients(org_id: str) -> list:
    """
    Collects all clients from Velociraptor.

    Returns:
        list: A list of all clients.
    """
    velociraptor_service = await UniversalService.create("Velociraptor")
    # query = create_query(
    #     "SELECT * FROM clients()",
    # )
    query = create_query(
        f"SELECT * FROM query(org_id='{org_id}', query='SELECT * FROM clients()')",
    )
    flow = velociraptor_service.execute_query(query)
    logger.info(f"Successfully ran artifact collection on {flow}")
    return flow["results"]


async def collect_velociraptor_organizations() -> list:
    """
    Collects all organizations from Velociraptor.

    Returns:
        list: A list of all organizations.
    """
    velociraptor_service = await UniversalService.create("Velociraptor")
    query = create_query(
        "SELECT * FROM orgs()",
    )
    flow = velociraptor_service.execute_query(query)
    logger.info(f"Successfully ran artifact collection on {flow}")
    return flow["results"]


async def collect_velociraptor_agent(agent_name: str) -> VelociraptorAgent:
    """
    Retrieves the client ID, last_seen_at and client version based on the agent name from Velociraptor.

    Args:
        agent_name (str): The name of the agent.

    Returns:
        str: The client ID if found, None otherwise.
        str: The last seen at timestamp if found, Default timsetamp otherwise.
    """
    logger.info(f"Collecting agent {agent_name} from Velociraptor")
    velociraptor_service = await UniversalService.create("Velociraptor")
    try:
        client_id = await velociraptor_service.get_client_id(agent_name)
        client_id = client_id["results"][0]["client_id"]
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Failed to get client ID for {agent_name}. Error: {e}")
        return VelociraptorAgent(
            client_id="Unknown",
            client_last_seen="Unknown",
            client_version="Unknown",
        )

    try:
        vql_last_seen_at = f"select last_seen_at from clients(search='host:{agent_name}')"
        last_seen_at = await velociraptor_service._get_last_seen_timestamp(
            vql_last_seen_at,
        )
        client_last_seen = datetime.fromtimestamp(
            int(last_seen_at) / 1000000,
        ).strftime(
            "%Y-%m-%dT%H:%M:%S+00:00",
        )  # Converting to string format
    except Exception as e:
        logger.error(
            f"Failed to get or convert last seen at for {agent_name}. Error: {e}",
        )
        client_last_seen = "1970-01-01T00:00:00+00:00"

    try:
        vql_client_version = f"select * from clients(search='host:{agent_name}')"
        # client_version = UniversalService()._get_client_version(vql_client_version)
        client_version = await velociraptor_service._get_client_version(
            vql_client_version,
        )
    except Exception as e:
        logger.error(f"Failed to get client version for {agent_name}. Error: {e}")
        client_version = "Unknown"

    return VelociraptorAgent(
        client_id=client_id,
        client_last_seen=client_last_seen,
        client_version=client_version,
    )


async def collect_velociraptor_agent_via_client_id(client_id: str) -> VelociraptorAgent:
    """
    Retrieves the client ID, last_seen_at and client version based on the agent name from Velociraptor.

    Args:
        agent_name (str): The name of the agent.

    Returns:
        str: The client ID if found, None otherwise.
        str: The last seen at timestamp if found, Default timsetamp otherwise.
    """
    logger.info(f"Collecting agent {client_id} from Velociraptor")
    velociraptor_service = await UniversalService.create("Velociraptor")
    try:
        client_id = await velociraptor_service.get_client_id_via_client_id(client_id)
        client_id = client_id["results"][0]["client_id"]
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Failed to get client ID for {client_id}. Error: {e}")
        return VelociraptorAgent(
            client_id="Unknown",
            client_last_seen="Unknown",
            client_version="Unknown",
        )

    try:
        vql_last_seen_at = f"select last_seen_at from clients(search='host:{client_id}')"
        last_seen_at = await velociraptor_service._get_last_seen_timestamp(
            vql_last_seen_at,
        )
        client_last_seen = datetime.fromtimestamp(
            int(last_seen_at) / 1000000,
        ).strftime(
            "%Y-%m-%dT%H:%M:%S+00:00",
        )  # Converting to string format
    except Exception as e:
        logger.error(
            f"Failed to get or convert last seen at for {client_id}. Error: {e}",
        )
        client_last_seen = "1970-01-01T00:00:00+00:00"

    try:
        vql_client_version = f"select * from clients(search='host:{client_id}')"
        # client_version = UniversalService()._get_client_version(vql_client_version)
        client_version = await velociraptor_service._get_client_version(
            vql_client_version,
        )
    except Exception as e:
        logger.error(f"Failed to get client version for {client_id}. Error: {e}")
        client_version = "Unknown"

    return VelociraptorAgent(
        client_id=client_id,
        client_last_seen=client_last_seen,
        client_version=client_version,
    )


def execute_query(universal_service, query: str) -> dict:
    """
    Executes a query using the provided universal service.

    Args:
        universal_service: The universal service to use for executing the query.
        query: The query to execute.

    Returns:
        A dictionary containing the result of the query execution.
    """
    flow = universal_service.execute_query(query)
    logger.info(f"Successfully ran artifact collection on {flow}")
    return flow


def check_flow_success(flow: dict, client_id: str) -> dict:
    """
    Checks the success status of a flow and returns a dictionary with a message and success status.

    Args:
        flow (dict): The flow dictionary containing the success status.
        client_id (str): The ID of the velociraptor client.

    Returns:
        dict: A dictionary with a message and success status.

    Raises:
        Exception: If there is an error while deleting the velociraptor client.
    """
    if flow["success"]:
        logger.info(f"Successfully deleted velociraptor client {client_id}")
        return {
            "message": f"Successfully deleted velociraptor client {client_id}",
            "success": True,
        }
    else:
        logger.error(f"Failed to delete velociraptor client {client_id}")
        return handle_exception(
            e="Failed to delete velociraptor client",
            client_id=client_id,
        )


def check_client_in_results(results: dict, client_id: str) -> dict:
    """
    Checks if a client is present in the results dictionary.

    Args:
        results (dict): The dictionary containing the results.
        client_id (str): The ID of the client to check.

    Returns:
        dict: A dictionary with a success message if the client is found, otherwise an error message.
    """
    if results["results"] == []:
        logger.info(f"Successfully deleted velociraptor client {client_id}")
        return {
            "message": f"Successfully deleted velociraptor client {client_id}",
            "success": True,
        }

    for result in results["results"]:
        if result["client_id"] == client_id:
            logger.error(f"Failed to delete velociraptor client {client_id}")
            return handle_exception(
                e="Failed to delete velociraptor client",
                client_id=client_id,
            )


def handle_exception(e: Exception, client_id: str) -> dict:
    """
    Handles exceptions that occur during the deletion of a Velociraptor client.

    Args:
        e (Exception): The exception that occurred.
        client_id (str): The ID of the client being deleted.

    Raises:
        HTTPException: An HTTP exception with a status code of 500 and a detailed error message.

    Returns:
        dict: An empty dictionary.
    """
    logger.error(f"Failed to delete client {client_id}: {e}")
    raise HTTPException(
        status_code=500,
        detail=f"Failed to delete Velociraptor client {client_id}: {e}",
    )


async def delete_agent_velociraptor(client_id: str) -> AgentModifyResponse:
    """
    Deletes an agent with the specified client ID.

    Args:
        client_id (str): The ID of the client to delete.

    Returns:
        AgentModifyResponse: An object representing the result of the agent deletion operation.
    """
    try:
        await delete_client(client_id=client_id)
        await ensure_client_deleted(client_id=client_id)
        return AgentModifyResponse(success=True, message="Agent deleted successfully")
    except Exception as e:
        return handle_exception(e, client_id)


async def delete_client(client_id: str) -> dict:
    """
    Deletes a client with the specified client ID.

    Args:
        client_id (str): The ID of the client to be deleted.

    Returns:
        dict: A dictionary containing the result of the deletion operation.
    """
    universal_service = await UniversalService.create("Velociraptor")
    try:
        query = create_query(
            f"SELECT collect_client(client_id='server', artifacts=['Server.Utils.DeleteClient'], env=dict(ClientIdList='{client_id}',ReallyDoIt='Y')) FROM scope()",
        )
        flow = execute_query(universal_service, query)
        return check_flow_success(flow, client_id)
    except Exception as e:
        return handle_exception(e, client_id)


async def ensure_client_deleted(client_id: str) -> dict:
    """
    Ensures that a client is deleted from the server.

    Args:
        client_id (str): The ID of the client to be deleted.

    Returns:
        dict: The result of the deletion operation.
    """
    universal_service = await UniversalService.create("Velociraptor")
    try:
        query = create_query(
            "SELECT collect_client(client_id='server', artifacts=['Server.Information.Clients'], env=dict()) FROM scope()",
        )
        flow = execute_query(universal_service, query)
        flow_id = (
            flow.get("results")[0]
            .get(
                "collect_client(client_id='server', artifacts=['Server.Information.Clients'], env=dict())",
            )
            .get("flow_id")
        )

        results = universal_service.read_collection_results(
            client_id=client_id,
            flow_id=flow_id,
            artifact="Server.Information.Clients",
        )
        return check_client_in_results(results, client_id)
    except Exception as e:
        return handle_exception(e, client_id)
