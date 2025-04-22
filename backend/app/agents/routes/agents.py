import asyncio
import csv
import io

# from fastapi import BackgroundTasks
from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Path
from fastapi import Security
from fastapi.responses import StreamingResponse
from loguru import logger
from packaging import version
from sqlalchemy import delete
from fastapi import Header
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.agents.schema.agents import AgentModifyResponse
from app.agents.schema.agents import AgentsResponse
from app.agents.schema.agents import AgentWazuhUpgradeResponse
from app.agents.schema.agents import OutdatedVelociraptorAgentsResponse
from app.agents.schema.agents import OutdatedWazuhAgentsResponse
from app.agents.schema.agents import SyncedAgentsResponse
from app.agents.services.status import get_agents_by_customer_code
from app.agents.services.status import get_outdated_agents_velociraptor
from app.agents.services.status import get_outdated_agents_wazuh
from app.agents.services.sync import sync_agents_velociraptor
from app.agents.services.sync import sync_agents_wazuh
from app.agents.velociraptor.services.agents import delete_agent_velociraptor
from app.agents.wazuh.schema.agents import VulnSeverity
from app.agents.wazuh.schema.agents import WazuhAgentScaPolicyResultsResponse
from app.agents.wazuh.schema.agents import WazuhAgentScaResponse
from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilitiesResponse
from app.agents.wazuh.services.agents import delete_agent_wazuh
from app.agents.wazuh.services.agents import upgrade_wazuh_agent
from app.agents.wazuh.services.sca import collect_agent_sca
from app.agents.wazuh.services.sca import collect_agent_sca_policy_results
from app.agents.wazuh.services.vulnerabilities import collect_agent_vulnerabilities
from app.agents.wazuh.services.vulnerabilities import collect_agent_vulnerabilities_new
from app.agents.wazuh.services.vulnerabilities import sync_agent_vulnerabilities

# App specific imports
from app.auth.routes.auth import AuthHandler
from app.connectors.wazuh_manager.utils.universal import send_get_request
from app.db.db_session import get_db

# App specific imports
# from app.db.db_session import session
from app.db.universal_models import Agents
from app.incidents.schema.db_operations import CaseOutResponse
from app.incidents.services.db_operations import list_cases_by_asset_name
from app.threat_intel.schema.epss import EpssThreatIntelRequest
from app.threat_intel.services.epss import collect_epss_score


async def get_wazuh_manager_version() -> str:
    """
    Fetches the version of the Wazuh Manager.

    Returns:
        str: The version of the Wazuh Manager.

    Raises:
        HTTPException: If there is an error fetching the version of the Wazuh Manager.
    """
    try:
        response = await send_get_request(endpoint="/")
        logger.info(f"Fetched Wazuh Manager version: {response}")
        return response["data"]["data"]["api_version"]
    except Exception as e:
        logger.error(f"Failed to fetch Wazuh Manager version: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Wazuh Manager version: {e}",
        )


async def check_wazuh_manager_version() -> bool:
    """
    Checks the version of the Wazuh Manager.

    Returns:
        bool: True if the version of the Wazuh Manager is 4.8.0 or higher, False otherwise.
    """
    try:
        wazuh_manager_version = await get_wazuh_manager_version()
        return version.parse(wazuh_manager_version) >= version.parse("4.8.0")
    except Exception as e:
        logger.error(f"Failed to check Wazuh Manager version: {e}")
        return False


agents_router = APIRouter()


async def fetch_velociraptor_id(db: AsyncSession, agent_id: str) -> str:
    """
    Fetches the velociraptor ID of an agent from the database.

    Args:
        db (AsyncSession): The database session.
        agent_id (str): The ID of the agent.

    Returns:
        str: The velociraptor ID of the agent.

    Raises:
        HTTPException: If the agent is not found in the database.
        HTTPException: If there is an error fetching the agent from the database.
    """
    try:
        result = await db.execute(select(Agents).filter(Agents.agent_id == agent_id))
        agent = result.scalars().first()
        if agent:
            return agent.velociraptor_id
        else:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    except Exception as e:
        logger.error(f"Failed to fetch agent {agent_id} from database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch agent {agent_id} from database: {e}",
        )


async def delete_agent_from_database(db: AsyncSession, agent_id: str):
    """
    Delete an agent from the database.

    Args:
        db (AsyncSession): The async database session.
        agent_id (str): The ID of the agent to be deleted.

    Raises:
        HTTPException: If there is an error deleting the agent from the database.

    """
    try:
        await db.execute(delete(Agents).filter(Agents.agent_id == agent_id))
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id} from database: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete agent {agent_id} from database: {e}",
        )


@agents_router.get(
    "",
    response_model=AgentsResponse,
    description="Get all agents currently synced to the database",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agents(db: AsyncSession = Depends(get_db)) -> AgentsResponse:
    """
    Retrieve all agents currently synced to the database.

    Returns:
        AgentsResponse: The response containing the list of agents, success status, and message.

    Raises:
        HTTPException: If there is an error while fetching the agents.
    """
    logger.info("Fetching all agents")
    try:
        result = await db.execute(select(Agents))
        agents = result.scalars().all()
        return AgentsResponse(
            agents=agents,
            success=True,
            message="Agents fetched successfully",
        )
    except Exception as e:
        logger.error(f"Failed to fetch agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch agents: {e}")

@agents_router.get(
    "/dashboard/agents",
    response_model=AgentsResponse,
    description="Get all Wazuh agents for a specific customer (Grafana dashboard use)",
)
async def get_customer_agents_for_dashboard(
    customer_code: Optional[str] = Header(None, description="Customer code to filter agents by"),
    db: AsyncSession = Depends(get_db)
) -> AgentsResponse:
    """
    Retrieve all agents for a specific customer for dashboard use.
    This endpoint is designed specifically for integration with Grafana dashboards.

    Args:
        customer_code (str, optional): The customer code from the request header.
        db (AsyncSession): The database session.

    Returns:
        AgentsResponse: The response containing the list of agents for the specified customer.

    Raises:
        HTTPException: If the customer_code is not provided or if there's an error fetching the agents.
    """
    if not customer_code:
        logger.warning("Dashboard agent request made with no customer_code header")
        return AgentsResponse(
            agents=[],
            success=False,
            message="No customer_code header provided",
        )

    logger.info(f"Fetching agents for customer_code: {customer_code} (dashboard request)")
    try:
        # Query agents with the specified customer code
        result = await db.execute(select(Agents).filter(Agents.customer_code == customer_code))
        agents = result.scalars().all()

        logger.info(f"Found {len(agents)} agents for customer_code: {customer_code}")
        return AgentsResponse(
            agents=agents,
            success=True,
            message=f"Agents for customer {customer_code} fetched successfully",
        )
    except Exception as e:
        logger.error(f"Failed to fetch agents for customer {customer_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch agents for customer {customer_code}"
        )


@agents_router.get(
    "/{agent_id}",
    response_model=AgentsResponse,
    description="Get agent by agent_id",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> AgentsResponse:
    """
    Retrieve an agent by agent_id.

    Args:
        agent_id (str): The ID of the agent to retrieve.
        db (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentsResponse: The response containing the agent information.

    Raises:
        HTTPException: If the agent with the specified agent_id is not found or if there is an error fetching the agent.
    """
    logger.info(f"Fetching agent with agent_id: {agent_id}")
    try:
        result = await db.execute(select(Agents).filter(Agents.agent_id == agent_id))
        agent = result.scalars().first()
        if agent:
            return AgentsResponse(
                agents=[agent],
                success=True,
                message="Agent fetched successfully",
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Agent with agent_id {agent_id} not found",
            )
    except Exception as e:
        logger.error(
            f"Failed to fetch agent: {agent_id} with error {e}. Does it exist?",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch agent: {agent_id}. Does it exist?",
        )


@agents_router.get(
    "/hostname/{hostname}",
    response_model=AgentsResponse,
    description="Get agent by hostname",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_by_hostname(
    hostname: str,
    db: AsyncSession = Depends(get_db),
) -> AgentsResponse:
    """
    Retrieve an agent by its hostname.

    Args:
        hostname (str): The hostname of the agent.
        db (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentsResponse: The response containing the agent information.

    Raises:
        HTTPException: If the agent with the specified hostname is not found or if there is an error fetching the agent.
    """
    logger.info(f"Fetching agent with hostname: {hostname}")
    try:
        result = await db.execute(select(Agents).filter(Agents.hostname == hostname))
        agent = result.scalars().first()
        if agent:
            return AgentsResponse(
                agents=[agent],
                success=True,
                message="Agent fetched successfully",
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Agent with hostname {hostname} not found",
            )
    except Exception as e:
        logger.error(f"Failed to fetch agent: {e}")
        # The exception message should not be exposed directly, especially in production
        raise HTTPException(status_code=500, detail="Failed to fetch agent")


@agents_router.post(
    "/sync",
    response_model=SyncedAgentsResponse,
    description="Sync agents from Wazuh Manager",
    dependencies=[
        Security(AuthHandler().require_any_scope("admin", "analyst", "scheduler")),
    ],
)
async def sync_all_agents() -> SyncedAgentsResponse:
    """
    Sync all agents from Wazuh Manager.

    This endpoint triggers the synchronization of all agents from the Wazuh Manager.
    It requires authentication with any of the following scopes: "admin", "analyst", "scheduler".

    Parameters:
    - backgroud_tasks (BackgroundTasks): The background tasks object used to add the sync_agents task.
    - session (AsyncSession, optional): The async session object used to interact with the database. Defaults to Depends(get_db).

    Returns:
    - SyncedAgentsResponse: The response model indicating the success of the sync operation.

    """
    logger.info("Syncing agents as part of scheduled job")
    loop = asyncio.get_event_loop()
    await loop.create_task(sync_agents_wazuh())
    await loop.create_task(sync_agents_velociraptor())
    return SyncedAgentsResponse(
        success=True,
        message="Agents synced started successfully",
    )


@agents_router.post(
    "/{agent_id}/critical",
    response_model=AgentModifyResponse,
    description="Mark agent as critical",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def mark_agent_as_critical(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
) -> AgentModifyResponse:
    """
    Marks the specified agent as critical.

    Args:
        agent_id (str): The ID of the agent to mark as critical.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentModifyResponse: The response indicating the success or failure of marking the agent as critical.
    """
    logger.info(f"Marking agent {agent_id} as critical")
    try:
        # Asynchronously fetch the agent by id
        result = await session.execute(
            select(Agents).filter(Agents.agent_id == agent_id),
        )
        agent = result.scalars().first()

        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent with agent_id {agent_id} not found",
            )

        agent.critical_asset = True
        await session.commit()

        return AgentModifyResponse(
            success=True,
            message=f"Agent {agent_id} marked as critical: {True}",
        )
    except Exception as e:
        session.rollback()  # Roll back the session in case of error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark agent as critical: {str(e)}",
        )


@agents_router.post(
    "/{agent_id}/noncritical",
    response_model=AgentModifyResponse,
    description="Mark agent as not critical",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def mark_agent_as_not_critical(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
) -> AgentModifyResponse:
    """
    Marks the specified agent as not critical.

    Args:
        agent_id (str): The ID of the agent to mark as not critical.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentModifyResponse: The response indicating the success or failure of the operation.

    Raises:
        HTTPException: If the agent with the specified ID is not found or if there is an error marking the agent as not critical.
    """
    logger.info(f"Marking agent {agent_id} as not critical")
    try:
        result = await session.execute(
            select(Agents).filter(Agents.agent_id == agent_id),
        )
        agent = result.scalars().first()

        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent with agent_id {agent_id} not found",
            )

        agent.critical_asset = False
        await session.commit()

        return AgentModifyResponse(
            success=True,
            message=f"Agent {agent_id} marked as not critical",
        )
    except Exception as e:
        await session.rollback()  # Roll back the session in case of error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark agent as not critical: {str(e)}",
        )


@agents_router.post(
    "/{agent_id}/wazuh/upgrade",
    response_model=AgentModifyResponse,
    description="Upgrade wazuh agent",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def upgrade_wazuh_agent_route(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
) -> AgentWazuhUpgradeResponse:
    """
    Upgrade Wazuh agent.

    Args:
        agent_id (str): The ID of the agent to be upgraded.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentModifyResponse: The response indicating the success or failure of the operation.
    """
    logger.info(f"Upgrading Wazuh agent {agent_id}")
    try:
        result = await session.execute(select(Agents).filter(Agents.agent_id == agent_id))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
        return await upgrade_wazuh_agent(agent_id)
        return AgentWazuhUpgradeResponse(
            success=True,
            message=f"Agent {agent_id} upgraded successfully started. Upgrade may take a few minutes to complete.",
        )
    except Exception as e:
        logger.error(f"Failed to upgrade Wazuh agent {agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upgrade Wazuh agent {agent_id}: {e}",
        )


@agents_router.get(
    "/{agent_id}/vulnerabilities/{vulnerability_severity}",
    response_model=WazuhAgentVulnerabilitiesResponse,
    description="Get agent vulnerabilities",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_vulnerabilities(
    agent_id: str,
    vulnerability_severity: VulnSeverity = Path(..., description="The severity of the vulnerabilities to fetch."),
) -> WazuhAgentVulnerabilitiesResponse:
    """
    Fetches the vulnerabilities of a specific agent.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        WazuhAgentVulnerabilitiesResponse: The response containing the agent vulnerabilities.
    """
    logger.info(f"Fetching agent {agent_id} vulnerabilities")
    wazuh_new = await check_wazuh_manager_version()
    if wazuh_new is True:
        logger.info("Wazuh Manager version is 4.8.0 or higher. Fetching vulnerabilities using new API")
        return await collect_agent_vulnerabilities_new(agent_id, vulnerability_severity.value)
    return await collect_agent_vulnerabilities(agent_id, vulnerability_severity.value)


@agents_router.get(
    "/{agent_id}/csv/vulnerabilities/{vulnerability_severity}",
    description="Get agent vulnerabilities as CSV",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_vulnerabilities_csv(agent_id: str, vulnerability_severity: VulnSeverity = Path(...)) -> StreamingResponse:
    """
    Fetches the vulnerabilities of a specific agent and returns them as a CSV file.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        StreamingResponse: The response containing the agent vulnerabilities in CSV format.
    """
    logger.info(f"Fetching agent {agent_id} vulnerabilities as CSV")
    wazuh_new = await check_wazuh_manager_version()
    if wazuh_new is True:
        logger.info("Wazuh Manager version is 4.8.0 or higher. Fetching vulnerabilities using new API")
        vulnerabilities = (
            await collect_agent_vulnerabilities_new(agent_id, vulnerability_severity=vulnerability_severity.value)
        ).vulnerabilities
    else:
        vulnerabilities = (
            await collect_agent_vulnerabilities(agent_id, vulnerability_severity=vulnerability_severity.value)
        ).vulnerabilities
    # Create a CSV file
    logger.info(f"Creating CSV file for agent {agent_id} with {len(vulnerabilities)} vulnerabilities")
    logger.info(f"Vulnerabilities: {vulnerabilities}")
    output = io.StringIO()
    writer = csv.writer(output)
    # Write the header
    writer.writerow(
        [
            "Severity",
            "Version",
            "Type",
            "Name",
            "External References",
            "Detection Time",
            "CVSS3 Score",
            "Published",
            "Architecture",
            "CVE",
            "Status",
            "Title",
            "EPSS Score",
        ],
    )
    # Write the rows
    for vulnerability in vulnerabilities:
        epss_score = await collect_epss_score(EpssThreatIntelRequest(cve=vulnerability.cve))
        writer.writerow(
            [
                vulnerability.severity,
                vulnerability.version,
                vulnerability.type,
                vulnerability.name,
                ", ".join(vulnerability.external_references) if vulnerability.external_references else "",
                vulnerability.detection_time,
                vulnerability.cvss3_score,
                vulnerability.published,
                vulnerability.architecture,
                vulnerability.cve,
                vulnerability.status,
                vulnerability.title,
                epss_score.data[0].epss if epss_score.data else "",
            ],
        )
    # Return the CSV file as a streaming response
    output.seek(0)
    return StreamingResponse(
        output,  # Use the StringIO object directly
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={agent_id}_vulnerabilities.csv"},
    )


@agents_router.get(
    "/{agent_id}/sca",
    response_model=WazuhAgentScaResponse,
    description="Get agent sca results",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_sca(agent_id: str) -> WazuhAgentScaResponse:
    """
    Fetches the sca results of a specific agent.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        WazuhAgentScaResponse: The response containing the agent sca.
    """
    logger.info(f"Fetching agent {agent_id} sca")
    return await collect_agent_sca(agent_id)


@agents_router.get(
    "/{agent_id}/sca/{policy_id}",
    response_model=WazuhAgentScaPolicyResultsResponse,
    description="Get agent sca results",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_sca_policy_results(agent_id: str, policy_id: str) -> WazuhAgentScaPolicyResultsResponse:
    """
    Fetches the sca results of a specific agent.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        WazuhAgentScaPolicyResultsResponse: The response containing the agent sca.
    """
    logger.info(f"Fetching agent {agent_id} sca policy results")
    return await collect_agent_sca_policy_results(agent_id, policy_id)


@agents_router.get(
    "/{agent_id}/csv/sca/{policy_id}",
    description="Get agent sca results as CSV",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_sca_policy_results_csv(agent_id: str, policy_id: str) -> StreamingResponse:
    """
    Fetches the sca results of a specific agent and returns them as a CSV file.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        StreamingResponse: The response containing the agent sca in CSV format.
    """
    logger.info(f"Fetching agent {agent_id} sca policy results as CSV")
    sca_results = (await collect_agent_sca_policy_results(agent_id, policy_id)).sca_policy_results
    # Create a CSV file
    logger.info(f"Creating CSV file for agent {agent_id} with {len(sca_results)} sca policy results")
    output = io.StringIO()
    writer = csv.writer(output)
    # Write the header
    writer.writerow(
        [
            "Description",
            "Policy ID",
            "Reason",
            "Command",
            "Rationale",
            "Condition",
            "Title",
            "Result",
            "Remediation",
            "Compliance",
            "Rules",
        ],
    )
    # Write the rows
    for sca_result in sca_results:
        writer.writerow(
            [
                sca_result.description,
                sca_result.policy_id,
                sca_result.reason,
                sca_result.command,
                sca_result.rationale,
                sca_result.condition,
                sca_result.title,
                sca_result.result,
                sca_result.remediation,
                ", ".join([f"{compliance.key}: {compliance.value}" for compliance in sca_result.compliance])
                if sca_result.compliance
                else "",
                ", ".join([f"{rule.type}: {rule.rule}" for rule in sca_result.rules]) if sca_result.rules else "",
            ],
        )
    # Return the CSV file as a streaming response
    output.seek(0)
    return StreamingResponse(
        output,  # Use the StringIO object directly
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={agent_id}_sca_policy_results.csv"},
    )


@agents_router.get(
    "/{agent_hostname}/cases",
    response_model=CaseOutResponse,
    description="Get cases for agent",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agent_soc_cases(agent_hostname: str, session: AsyncSession = Depends(get_db)):
    """
    Fetches the SOC cases of a specific agent.

    Args:
        agent_id (str): The ID of the agent.

    Returns:
        SocCasesResponse: The response containing the agent SOC cases.
    """
    logger.info(f"Fetching agent {agent_hostname} cases")
    return CaseOutResponse(
        cases=await list_cases_by_asset_name(asset_name=agent_hostname, db=session),
        success=True,
        message="Cases retrieved successfully",
    )


@agents_router.get(
    "/wazuh/outdated",
    response_model=OutdatedWazuhAgentsResponse,
    description="Get all outdated Wazuh agents",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_outdated_wazuh_agents(
    session: AsyncSession = Depends(get_db),
) -> OutdatedWazuhAgentsResponse:
    """
    Retrieve all outdated Wazuh agents.

    This endpoint requires the user to have either the "admin" or "analyst" scope.

    Returns:
        OutdatedWazuhAgentsResponse: The response containing the outdated Wazuh agents.
    """
    logger.info("Fetching all outdated Wazuh agents")
    return await get_outdated_agents_wazuh(session)


@agents_router.get(
    "/velociraptor/outdated",
    response_model=OutdatedVelociraptorAgentsResponse,
    description="Get all outdated Velociraptor agents",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_outdated_velociraptor_agents(
    session: AsyncSession = Depends(get_db),
) -> OutdatedVelociraptorAgentsResponse:
    """
    Fetches all outdated Velociraptor agents.

    Parameters:
    - session: The database session.

    Returns:
    - OutdatedVelociraptorAgentsResponse: The response containing the outdated Velociraptor agents.
    """
    logger.info("Fetching all outdated Velociraptor agents")
    return await get_outdated_agents_velociraptor(session)


@agents_router.put(
    "/{agent_id}/update",
    response_model=AgentModifyResponse,
    description="Update agent",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_agent(
    agent_id: str,
    velociraptor_id: str,
    session: AsyncSession = Depends(get_db),
) -> AgentModifyResponse:
    """
    Updates an agent's velociraptor_id

    Args:
        agent_id (str): The ID of the agent to be updated.
        velociraptor_id (str): The new velociraptor_id of the agent.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentModifyResponse: The response indicating the success or failure of the update.
    """
    logger.info(f"Updating agent {agent_id} with Velociraptor ID: {velociraptor_id}")
    try:
        result = await session.execute(select(Agents).filter(Agents.agent_id == agent_id))
        agent = result.scalars().first()
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
        agent.velociraptor_id = velociraptor_id
        await session.commit()
        logger.info(f"Agent {agent_id} updated with Velociraptor ID: {velociraptor_id}")
        return AgentModifyResponse(
            success=True,
            message=f"Agent {agent_id} updated with Velociraptor ID: {velociraptor_id}",
        )
    except Exception as e:
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
        logger.error(f"Failed to update agent {agent_id} with Velociraptor ID: {velociraptor_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update agent {agent_id} with Velociraptor ID: {velociraptor_id}: {e}",
        )


@agents_router.delete(
    "/{agent_id}/delete",
    response_model=AgentModifyResponse,
    description="Delete agent",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
) -> AgentModifyResponse:
    """
    Delete an agent.

    Args:
        agent_id (str): The ID of the agent to be deleted.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentModifyResponse: The response indicating the success or failure of the deletion.
    """
    logger.info(f"Deleting agent {agent_id}")
    await delete_agent_wazuh(agent_id)
    client_id = await fetch_velociraptor_id(db=session, agent_id=agent_id)
    logger.info(f"Client ID: {client_id}")
    if client_id != "Unknown":
        await delete_agent_velociraptor(client_id)
    await delete_agent_from_database(db=session, agent_id=agent_id)
    return AgentModifyResponse(
        success=True,
        message=f"Agent {agent_id} deleted successfully",
    )


@agents_router.get(
    "/sync/vulnerabilities",
    description="Sync agent vulnerabilities",
)
async def sync_vulnerabilities_route(
    session: AsyncSession = Depends(get_db),
):
    """
    Only applies to Wazuh Manager Version 4.8.1 or higher.
    1. Loops through all agents in the database to collect their agent_name and customer code.
    2. Queries the `wazuh-states-vulnerabilities-*` index in Wazuh Indexer to get vulnerabilities based on the agent_name.
    3. Checks the `wazuh-vulnerabilities-*customer_code*` index in Wazuh Indexer to get vulnerabilities based on the
        agent_name and checks to see if a vulnerability_id already exists.
    4. If the vulnerability_id does not exist, it is sent to the Graylog GELF Input.
    """
    logger.info("Syncing agent vulnerabilities")
    agents = await get_agents(session)
    for agent in agents.agents:
        if agent.customer_code is None:
            logger.info(f"Skipping agent {agent.hostname} due to missing customer code")
            continue
        await sync_agent_vulnerabilities(agent.hostname, agent.customer_code)
    return {"success": True, "message": "Agent vulnerabilities synced successfully"}


@agents_router.post(
    "/sync/vulnerabilities/{customer_code}",
    description="Sync agent vulnerabilities",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def sync_vulnerabilities_customer_code_route(
    customer_code: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    logger.info("Syncing agent vulnerabilities")
    agents = await get_agents_by_customer_code(customer_code, session)
    for agent in agents:
        if agent.customer_code is None:
            logger.info(f"Skipping agent {agent.hostname} due to missing customer code")
            continue
        background_tasks.add_task(sync_agent_vulnerabilities, agent.hostname, customer_code)
    return {"success": True, "message": "Agent vulnerabilities sync initiated successfully"}


# ! TODO: CURRENTLY UPDATES IN THE DB BUT NEED TO UPDATE IN WAZUH # !
# @agents_router.put(
#     "/{agent_id}/update-customer-code",
#     response_model=AgentUpdateCustomerCodeResponse,
#     description="Update `agent` customer code",
#     dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
# )
# async def update_agent_customer_code(agent_id: str, body: AgentUpdateCustomerCodeBody, db: AsyncSession = Depends(get_db)) -> AgentUpdateCustomerCodeResponse:
#     logger.info(f"Updating agent {agent_id} customer code to {body.customer_code}")
#     try:
#         result = await db.execute(select(Agents).filter(Agents.agent_id == agent_id))
#         agent = result.scalars().first()
#         if not agent:
#             raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
#         agent.customer_code = body.customer_code
#         await db.commit()
#         logger.info(f"Agent {agent_id} customer code updated to {body.customer_code}")
#         return {"success": True, "message": f"Agent {agent_id} customer code updated to {body.customer_code}"}
#     except Exception as e:
#         if not agent:
#             raise HTTPException(status_code=404, detail=f"Agent with agent_id {agent_id} not found")
