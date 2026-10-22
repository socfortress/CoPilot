"""Deleting an agent everywhere it lives: the Wazuh manager, Velociraptor and CoPilot's own rows.

Shared by the agents' bulk routes and the healthcheck's "delete unhealthy agents" (#1291). Every
deletion writes an ``agent.delete`` audit row, like the single-agent route always has.
"""

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import List
from typing import Optional
from typing import Union

from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schema.agents import BulkDeleteAgentResult
from app.agents.velociraptor.services.agents import delete_agent_velociraptor
from app.agents.wazuh.services.agents import delete_agent_wazuh
from app.audit.models.audit import AuditAction
from app.audit.models.audit import AuditResult
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.db.universal_models import AgentDataStore
from app.db.universal_models import Agents
from app.db.universal_models import AgentVulnerabilities

WAZUH = "wazuh"
VELOCIRAPTOR = "velociraptor"


@dataclass(frozen=True)
class AgentRef:
    """The agent's row, copied before anything is deleted.

    A rollback expires every ORM object in the session, and reading an expired one under an
    AsyncSession raises; a loop deleting many agents therefore works from these copies.
    """

    agent_id: str
    customer_code: Optional[str]
    hostname: Optional[str]
    velociraptor_id: Optional[str]
    wazuh_last_seen: Optional[datetime]
    velociraptor_last_seen: Optional[datetime]

    @classmethod
    def of(cls, agent: Union[Agents, "AgentRef"]) -> "AgentRef":
        if isinstance(agent, AgentRef):
            return agent
        return cls(
            agent_id=agent.agent_id,
            customer_code=agent.customer_code,
            hostname=agent.hostname,
            velociraptor_id=agent.velociraptor_id,
            wazuh_last_seen=agent.wazuh_last_seen,
            velociraptor_last_seen=agent.velociraptor_last_seen,
        )

    @property
    def has_velociraptor_client(self) -> bool:
        return bool(self.velociraptor_id) and self.velociraptor_id != "Unknown"


@dataclass
class AgentDeletion:
    """What deleting one agent did. ``deleted`` means CoPilot's row is gone; an upstream that did not
    confirm (the agent may still be enrolled there) is named in ``upstream_failures``."""

    agent_id: str
    deleted: bool
    upstream_failures: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


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
        # First delete related records from agent_datastore
        await db.execute(delete(AgentDataStore).filter(AgentDataStore.agent_id == agent_id))
        # ...and the agent's vulnerabilities. The FK cascades on delete, but doing it
        # explicitly keeps the delete working on databases that predate that migration.
        await db.execute(delete(AgentVulnerabilities).filter(AgentVulnerabilities.agent_id == agent_id))
        # Then delete the agent
        await db.execute(delete(Agents).filter(Agents.agent_id == agent_id))
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id} from database: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete agent {agent_id} from database: {e}",
        )


def agent_snapshot(agent: AgentRef) -> dict:
    """The agent as it was, for the audit row: who it was and when each tool last saw it."""
    return {
        "hostname": agent.hostname,
        "customer_code": agent.customer_code,
        "velociraptor_id": agent.velociraptor_id,
        "wazuh_last_seen": agent.wazuh_last_seen.isoformat() if agent.wazuh_last_seen else None,
        "velociraptor_last_seen": agent.velociraptor_last_seen.isoformat() if agent.velociraptor_last_seen else None,
    }


def _error_text(error: Exception) -> str:
    return str(error.detail) if isinstance(error, HTTPException) else str(error)


async def delete_agent_everywhere(
    db: AsyncSession,
    agent: Union[Agents, AgentRef],
    *,
    actor: Optional[User],
    via: str,
    context: Optional[dict] = None,
    request: Optional[Request] = None,
) -> AgentDeletion:
    """
    Delete one agent from Wazuh, from Velociraptor (when it has a client there) and from CoPilot,
    in that order, and audit it as ``agent.delete``.

    An upstream that refuses or cannot be reached does not stop CoPilot's own deletion: the result
    says which one did not confirm. Never raises.

    Args:
        db (AsyncSession): The database session.
        agent (Agents | AgentRef): The agent's row, read before the deletion.
        actor (User): Who asked; recorded on the audit row.
        via (str): Which path deleted it (``bulk_delete``, ``healthcheck``, …); recorded on the audit row.
        context (dict): Anything else the audit row should carry, e.g. the healthcheck's threshold.
        request (Request): The incoming request, for the audit row's source address.

    Returns:
        AgentDeletion: What was deleted and what did not confirm.
    """
    agent = AgentRef.of(agent)
    agent_id = agent.agent_id
    snapshot = agent_snapshot(agent)
    result = AgentDeletion(agent_id=agent_id, deleted=False)

    try:
        await delete_agent_wazuh(agent_id)
    except Exception as e:
        logger.warning(f"Agent {agent_id}: Wazuh did not confirm the deletion: {_error_text(e)}")
        result.upstream_failures.append(WAZUH)
        result.errors.append(f"Failed to delete from Wazuh: {_error_text(e)}")

    if agent.has_velociraptor_client:
        try:
            await delete_agent_velociraptor(agent.velociraptor_id)
        except Exception as e:
            logger.warning(f"Agent {agent_id}: Velociraptor did not confirm the deletion: {_error_text(e)}")
            result.upstream_failures.append(VELOCIRAPTOR)
            result.errors.append(f"Failed to delete from Velociraptor: {_error_text(e)}")

    try:
        await delete_agent_from_database(db=db, agent_id=agent_id)
        result.deleted = True
    except Exception as e:
        result.errors.append(f"Failed to delete from database: {_error_text(e)}")

    await record_audit_event(
        action=AuditAction.AGENT_DELETE,
        actor_user_id=actor.id if actor else None,
        actor_username=actor.username if actor else None,
        customer_code=agent.customer_code,
        entity_type="agent",
        entity_id=agent_id,
        result=AuditResult.SUCCESS if result.deleted else AuditResult.FAILURE,
        old_value=snapshot,
        new_value={"via": via, **(context or {})},
        details="; ".join(result.errors) if result.errors else None,
        request=request,
    )
    return result


async def delete_single_agent(
    db: AsyncSession,
    agent_id: str,
    agent: Union[Agents, AgentRef],
    *,
    actor: Optional[User] = None,
    via: str = "bulk_delete",
    request: Optional[Request] = None,
) -> BulkDeleteAgentResult:
    """
    Delete a single agent and return the result.
    This function handles errors gracefully and returns a result object.

    Args:
        db (AsyncSession): The database session.
        agent_id (str): The ID of the agent to delete.
        agent (Agents): The agent object from the database.
        actor (User): Who asked; recorded on the audit row.
        via (str): Which path deleted it; recorded on the audit row.
        request (Request): The incoming request, for the audit row's source address.

    Returns:
        BulkDeleteAgentResult: The result of the deletion attempt.
    """
    deletion = await delete_agent_everywhere(db, agent, actor=actor, via=via, request=request)

    if not deletion.deleted:
        return BulkDeleteAgentResult(
            agent_id=agent_id,
            success=False,
            message=f"Failed to delete agent: {'; '.join(deletion.errors)}",
        )

    if deletion.errors:
        return BulkDeleteAgentResult(
            agent_id=agent_id,
            success=True,
            message=f"Agent deleted from database but with warnings: {'; '.join(deletion.errors)}",
        )

    return BulkDeleteAgentResult(
        agent_id=agent_id,
        success=True,
        message="Agent deleted successfully",
    )
