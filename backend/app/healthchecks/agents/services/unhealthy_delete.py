"""Deleting a customer's unhealthy agents from the healthcheck lists (#1291).

The browser sends the agents it listed and the threshold the user chose; nothing is trusted from the
list it read. Each agent is judged again here, at the time of the request, by ``judge``: the preview
answers with that judgement and the deletion acts on it, so what the dialog shows is what runs.
"""

from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.agents.services.deletion import VELOCIRAPTOR
from app.agents.services.deletion import WAZUH
from app.agents.services.deletion import AgentRef
from app.agents.services.deletion import delete_agent_everywhere
from app.auth.models.users import User
from app.db.universal_models import Agents
from app.db.universal_models import Customers
from app.healthchecks.agents.schema.unhealthy_delete import AgentVerdict
from app.healthchecks.agents.schema.unhealthy_delete import HealthcheckSource
from app.healthchecks.agents.schema.unhealthy_delete import UnhealthyAgentDeleteResult
from app.healthchecks.agents.schema.unhealthy_delete import UnhealthyAgentPreview
from app.healthchecks.agents.schema.unhealthy_delete import UnhealthyAgentsDeleteRequest
from app.healthchecks.agents.schema.unhealthy_delete import (
    UnhealthyAgentsDeleteResponse,
)
from app.healthchecks.agents.schema.unhealthy_delete import (
    UnhealthyAgentsPreviewRequest,
)
from app.healthchecks.agents.schema.unhealthy_delete import (
    UnhealthyAgentsPreviewResponse,
)
from app.healthchecks.agents.schema.unhealthy_delete import VerdictCounts
from app.time_utils import now_utc
from app.time_utils import to_naive_utc

WAZUH_MANAGER_ID = "000"


def other_tool(source: HealthcheckSource) -> HealthcheckSource:
    return VELOCIRAPTOR if source == WAZUH else WAZUH


def last_seen(agent: AgentRef, tool: HealthcheckSource) -> Optional[datetime]:
    if tool == VELOCIRAPTOR:
        return agent.velociraptor_last_seen if agent.has_velociraptor_client else None
    return agent.wazuh_last_seen


def is_stale(agent: AgentRef, tool: HealthcheckSource, threshold: timedelta, now: datetime) -> bool:
    """Whether ``tool`` has not seen the agent for more than ``threshold``.

    Never seen (no time, or no Velociraptor client at all) is stale. A time after ``now`` is not: the
    healthcheck list flags it, but it means a clock ahead of ours saw the agent, not that it is gone.
    """
    seen = last_seen(agent, tool)
    if seen is None:
        return True
    if seen > now:
        return False
    return now - seen > threshold


def judge(agent: Optional[AgentRef], source: HealthcheckSource, threshold: timedelta, now: datetime) -> AgentVerdict:
    """What deleting this agent from the ``source`` list would do, at ``now``."""
    if agent is None:
        return AgentVerdict.NOT_FOUND
    if agent.agent_id == WAZUH_MANAGER_ID:
        return AgentVerdict.WAZUH_MANAGER
    if not is_stale(agent, source, threshold, now):
        return AgentVerdict.SEEN_RECENTLY
    if not is_stale(agent, other_tool(source), threshold, now):
        return AgentVerdict.ACTIVE_ELSEWHERE
    return AgentVerdict.DELETABLE


def count_verdicts(verdicts: List[AgentVerdict]) -> VerdictCounts:
    counts = VerdictCounts()
    for verdict in verdicts:
        setattr(counts, verdict.value, getattr(counts, verdict.value) + 1)
    return counts


def judgement_time() -> datetime:
    """Now, as the naive UTC the ``agents`` columns hold."""
    return to_naive_utc(now_utc())


async def _customer_agents(session: AsyncSession, customer_code: str, agent_ids: List[str]) -> Dict[str, Agents]:
    """The customer's rows among ``agent_ids``; another customer's agent is simply not found."""
    customer = (await session.execute(select(Customers.customer_code).where(Customers.customer_code == customer_code))).first()
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer with customer_code {customer_code} not found")
    rows = await session.execute(select(Agents).where(Agents.customer_code == customer_code, Agents.agent_id.in_(agent_ids)))
    return {row.agent_id: row for row in rows.scalars().all()}


async def preview_unhealthy_agents(
    session: AsyncSession,
    customer_code: str,
    source: HealthcheckSource,
    body: UnhealthyAgentsPreviewRequest,
) -> UnhealthyAgentsPreviewResponse:
    """Judge each requested agent as the deletion would, and change nothing."""
    rows = await _customer_agents(session, customer_code, body.agent_ids)
    threshold = body.not_seen_for.delta
    now = judgement_time()

    agents: List[UnhealthyAgentPreview] = []
    for agent_id in body.agent_ids:
        row = rows.get(agent_id)
        ref = AgentRef.of(row) if row is not None else None
        verdict = judge(ref, source, threshold, now)
        if ref is None:
            agents.append(UnhealthyAgentPreview(agent_id=agent_id, verdict=verdict))
            continue
        agents.append(
            UnhealthyAgentPreview(
                agent_id=agent_id,
                verdict=verdict,
                hostname=row.hostname,
                label=row.label,
                os=row.os,
                last_seen=last_seen(ref, source),
                other_last_seen=last_seen(ref, other_tool(source)),
            ),
        )

    counts = count_verdicts([agent.verdict for agent in agents])
    return UnhealthyAgentsPreviewResponse(
        success=True,
        message=f"{counts.deletable} of {len(agents)} agents can be deleted",
        source=source,
        not_seen_for=body.not_seen_for,
        cutoff=now - threshold,
        counts=counts,
        agents=agents,
    )


def _summary(deleted: int, skipped: int, failed: int, unconfirmed: int) -> str:
    parts = [f"{deleted} deleted"]
    if unconfirmed:
        parts.append(f"{unconfirmed} not confirmed upstream")
    if skipped:
        parts.append(f"{skipped} skipped")
    if failed:
        parts.append(f"{failed} failed")
    return ", ".join(parts)


async def delete_unhealthy_agents(
    session: AsyncSession,
    customer_code: str,
    source: HealthcheckSource,
    body: UnhealthyAgentsDeleteRequest,
    actor: User,
    request: Optional[Request] = None,
) -> UnhealthyAgentsDeleteResponse:
    """
    Judge each requested agent again and delete the deletable ones from Wazuh, Velociraptor and
    CoPilot, one at a time, each audited as ``agent.delete`` with the threshold it was deleted under.

    An agent active on the other tool is deleted only with ``include_active_elsewhere``. Anything
    else not deletable now (seen since the list was read, unknown, another customer's, the Wazuh
    manager) is skipped with its verdict, never an error: one stale row must not stop the rest.
    """
    rows = await _customer_agents(session, customer_code, body.agent_ids)
    # Copied before the first deletion: a rollback would expire the rows still to come.
    refs = {agent_id: AgentRef.of(row) for agent_id, row in rows.items()}
    threshold = body.not_seen_for.delta
    now = judgement_time()
    context = {
        "source": source,
        "not_seen_for": body.not_seen_for.label,
        "include_active_elsewhere": body.include_active_elsewhere,
    }
    logger.info(
        f"Deleting up to {len(body.agent_ids)} {source} agents of {customer_code} unseen for over {body.not_seen_for.label}",
    )

    results: List[UnhealthyAgentDeleteResult] = []
    for agent_id in body.agent_ids:
        ref = refs.get(agent_id)
        verdict = judge(ref, source, threshold, now)
        if verdict == AgentVerdict.ACTIVE_ELSEWHERE and body.include_active_elsewhere:
            verdict = AgentVerdict.DELETABLE
        if verdict != AgentVerdict.DELETABLE:
            hostname = ref.hostname if ref is not None else None
            results.append(UnhealthyAgentDeleteResult(agent_id=agent_id, hostname=hostname, outcome="skipped", reason=verdict))
            continue

        deletion = await delete_agent_everywhere(session, ref, actor=actor, via="healthcheck", context=context, request=request)
        results.append(
            UnhealthyAgentDeleteResult(
                agent_id=agent_id,
                hostname=ref.hostname,
                outcome="deleted" if deletion.deleted else "failed",
                unconfirmed=deletion.upstream_failures,
            ),
        )

    deleted = sum(1 for result in results if result.outcome == "deleted")
    skipped = sum(1 for result in results if result.outcome == "skipped")
    failed = sum(1 for result in results if result.outcome == "failed")
    unconfirmed = sum(1 for result in results if result.outcome == "deleted" and result.unconfirmed)
    logger.info(f"Unhealthy {source} agents of {customer_code}: {_summary(deleted, skipped, failed, unconfirmed)}")
    return UnhealthyAgentsDeleteResponse(
        success=failed == 0,
        message=_summary(deleted, skipped, failed, unconfirmed),
        source=source,
        not_seen_for=body.not_seen_for,
        requested=len(body.agent_ids),
        deleted=deleted,
        skipped=skipped,
        failed=failed,
        unconfirmed=unconfirmed,
        results=results,
    )
