"""The Exposure page's compliance (#1289): SCA results across a tenant, by policy.

The Wazuh manager answers SCA one agent at a time (``GET /sca/{agent}``), the call each
agent's SCA tab already makes (#1256). Across a tenant that is one call per agent, so:

* the calls run concurrently, at most ``MAX_CONCURRENT`` at once;
* the results are **kept for ``CACHE_TTL_SECONDS``** per set of agents (SCA scans run every
  few hours), so opening a policy or coming back to the tab asks Wazuh nothing;
* an agent Wazuh cannot answer for is **counted, not hidden**: ``unavailable_agents`` says
  how many are missing, and when none could be read the response is an error rather than a
  page that reads "nothing assessed";
* the manager's error text stays in the log.

Averages are over agent × policy results; a policy is "weak" on an agent under ``WEAK_SCORE``.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from loguru import logger

from app.agents.wazuh.schema.agents import WazuhAgentScaResults
from app.agents.wazuh.services.sca import collect_agent_sca
from app.customer_portal.schema.exposure import ComplianceResponse
from app.customer_portal.schema.exposure import PolicyAgent
from app.customer_portal.schema.exposure import PolicyAgentsResponse
from app.customer_portal.schema.exposure import PolicyRow
from app.customer_portal.services.exposure import ExposureScope
from app.customer_portal.services.exposure import ScopedAgent

MAX_CONCURRENT = 20
WEAK_SCORE = 50
READ_ERROR = "The compliance data could not be read from Wazuh"


def cache_ttl() -> float:
    try:
        return max(0.0, float(os.getenv("EXPOSURE_CACHE_TTL_SECONDS", "300")))
    except ValueError:
        return 300.0


@dataclass
class ScaSnapshot:
    """What Wazuh answered for a set of agents, and when."""

    results: List[Tuple[ScopedAgent, List[WazuhAgentScaResults]]] = field(default_factory=list)
    unavailable: int = 0
    read_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_cache: Dict[Tuple, Tuple[float, ScaSnapshot]] = {}
_lock = asyncio.Lock()


def clear_cache() -> None:
    _cache.clear()


def _key(scope: ExposureScope) -> Tuple:
    return tuple(sorted((agent.agent_id, agent.hostname, agent.customer_code) for agent in scope.agents))


async def _read_agent(agent: ScopedAgent, semaphore: asyncio.Semaphore) -> Optional[List[WazuhAgentScaResults]]:
    """The agent's policies; None when Wazuh could not answer for it."""
    async with semaphore:
        try:
            response = await collect_agent_sca(agent.agent_id)
            return list(response.sca or [])
        except Exception as e:
            logger.warning(f"Customer portal exposure: SCA of agent {agent.agent_id} could not be read: {type(e).__name__}")
            return None


async def read_snapshot(scope: ExposureScope) -> ScaSnapshot:
    """The scope's SCA, from the cache while it is fresh, else from Wazuh."""
    key = _key(scope)
    async with _lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < cache_ttl():
            return cached[1]
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    answers = await asyncio.gather(*(_read_agent(agent, semaphore) for agent in scope.agents))
    snapshot = ScaSnapshot()
    for agent, policies in zip(scope.agents, answers):
        if policies is None:
            snapshot.unavailable += 1
        else:
            snapshot.results.append((agent, policies))
    # A read where Wazuh answered for no agent is not kept: the next request tries again.
    if not scope.agents or snapshot.unavailable < len(scope.agents):
        async with _lock:
            _cache[key] = (time.monotonic(), snapshot)
    return snapshot


# ── shaping (pure) ────────────────────────────────────────────────────────────


def summarize(snapshot: ScaSnapshot) -> Tuple[List[PolicyRow], Dict[str, object]]:
    """Policies, weakest average first, and the figures across them."""
    by_policy: Dict[str, List[Tuple[ScopedAgent, WazuhAgentScaResults]]] = {}
    for agent, policies in snapshot.results:
        for policy in policies:
            by_policy.setdefault(policy.policy_id, []).append((agent, policy))

    rows = []
    for policy_id, entries in by_policy.items():
        scores = [result.score for _, result in entries]
        named = next((result for _, result in entries if result.name), entries[0][1])
        rows.append(
            PolicyRow(
                policy_id=policy_id,
                name=named.name,
                description=named.description,
                agents=len({agent.agent_id for agent, _ in entries}),
                average_score=round(sum(scores) / len(scores), 1),
                min_score=min(scores),
                passed=sum(result.pass_count for _, result in entries),
                failed=sum(result.fail for _, result in entries),
                invalid=sum(result.invalid for _, result in entries),
                agents_below=sum(1 for score in scores if score < WEAK_SCORE),
            ),
        )
    rows.sort(key=lambda row: (row.average_score, (row.name or row.policy_id).lower()))

    all_results = [result for _, policies in snapshot.results for result in policies]
    figures = {
        "agents_assessed": sum(1 for _, policies in snapshot.results if policies),
        "average_score": round(sum(result.score for result in all_results) / len(all_results), 1) if all_results else None,
        "passed": sum(result.pass_count for result in all_results),
        "failed": sum(result.fail for result in all_results),
    }
    return rows, figures


def policy_agents(snapshot: ScaSnapshot, policy_id: str) -> Tuple[Optional[str], List[PolicyAgent]]:
    """The agents assessed on one policy, weakest score first."""
    name = None
    agents = []
    for agent, policies in snapshot.results:
        for result in policies:
            if result.policy_id != policy_id:
                continue
            name = name or result.name
            agents.append(
                PolicyAgent(
                    agent_id=agent.agent_id,
                    hostname=agent.hostname,
                    customer_code=agent.customer_code,
                    score=result.score,
                    passed=result.pass_count,
                    failed=result.fail,
                    invalid=result.invalid,
                    end_scan=result.end_scan,
                ),
            )
    agents.sort(key=lambda row: (row.score, row.hostname.lower()))
    return name, agents


def _utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── the page ──────────────────────────────────────────────────────────────────


async def compliance(scope: ExposureScope) -> ComplianceResponse:
    response = ComplianceResponse(
        enabled=scope.enabled,
        customer_codes=scope.customer_codes,
        agents_in_scope=len(scope.agents),
        weak_score=WEAK_SCORE,
        message="The Exposure page is not enabled for this customer" if not scope.enabled else "Compliance retrieved",
    )
    if not scope.agents:
        return response
    snapshot = await read_snapshot(scope)
    response.unavailable_agents = snapshot.unavailable
    response.read_at = _utc(snapshot.read_at)
    if snapshot.unavailable == len(scope.agents):
        response.error = READ_ERROR
        return response
    response.policies, figures = summarize(snapshot)
    response.agents_assessed = figures["agents_assessed"]
    response.average_score = figures["average_score"]
    response.passed = figures["passed"]
    response.failed = figures["failed"]
    return response


async def compliance_policy(scope: ExposureScope, policy_id: str) -> PolicyAgentsResponse:
    if not scope.agents:
        return PolicyAgentsResponse(policy_id=policy_id)
    snapshot = await read_snapshot(scope)
    if snapshot.unavailable == len(scope.agents):
        return PolicyAgentsResponse(policy_id=policy_id, error=READ_ERROR)
    name, agents = policy_agents(snapshot, policy_id)
    return PolicyAgentsResponse(policy_id=policy_id, name=name, agents=agents)
