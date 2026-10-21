"""The Customer Portal's Exposure page (#1289): the switch, and the agents a caller's view covers.

* **Opt-in per customer.** ``customer_portal_exposure_settings`` is the operator's switch; a
  missing row reads as off. The caller's customers are narrowed to those whose switch is on
  *before* Wazuh is asked anything, so a disabled customer's agents are never even named in
  a query.
* **The agents are the tenant key.** Wazuh knows agents, not customers, so a view is the
  ``agents`` rows of those customers. The vulnerability index is then filtered by both the
  agents' Wazuh ids *and* their names (an id is unique per manager only), and SCA is asked
  agent by agent. Every other part of the page builds on ``ExposureScope``.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.db.universal_models import Agents
from app.db.universal_models import CustomerPortalExposureSettings
from app.middleware.customer_access import customer_access_handler
from app.time_utils import now_utc


@dataclass(frozen=True)
class ScopedAgent:
    agent_id: str
    hostname: str
    customer_code: str


@dataclass
class ExposureScope:
    """The customers a view covers (switch on, visible to the caller) and their agents."""

    customer_codes: List[str] = field(default_factory=list)
    agents: List[ScopedAgent] = field(default_factory=list)

    @property
    def enabled(self) -> bool:
        return bool(self.customer_codes)

    @property
    def agent_ids(self) -> List[str]:
        return sorted({agent.agent_id for agent in self.agents})

    @property
    def hostnames(self) -> List[str]:
        return sorted({agent.hostname for agent in self.agents})

    def by_agent(self) -> Dict[Tuple[str, str], ScopedAgent]:
        """Agents keyed by (Wazuh id, name): what a Wazuh document names."""
        return {(agent.agent_id, agent.hostname): agent for agent in self.agents}

    def owner(self, agent_id: Optional[str], hostname: Optional[str]) -> Optional[ScopedAgent]:
        """The scope's agent a Wazuh document names, or None when it is not one of them."""
        return self.by_agent().get((agent_id or "", hostname or ""))


# ── the switch ───────────────────────────────────────────────────────────────


async def get_exposure_settings(customer_code: str, session: AsyncSession) -> Optional[CustomerPortalExposureSettings]:
    result = await session.execute(
        select(CustomerPortalExposureSettings).where(CustomerPortalExposureSettings.customer_code == customer_code),
    )
    return result.scalars().first()


async def upsert_exposure_settings(
    customer_code: str,
    enabled: bool,
    session: AsyncSession,
    user_id: Optional[int] = None,
) -> CustomerPortalExposureSettings:
    """Create or update a customer's switch. Caller commits."""
    settings = await get_exposure_settings(customer_code, session)
    if settings is None:
        settings = CustomerPortalExposureSettings(customer_code=customer_code)
        session.add(settings)
    settings.enabled = enabled
    settings.updated_at = now_utc()
    settings.updated_by = user_id
    return settings


async def enabled_customer_codes(user: User, session: AsyncSession, requested: Optional[List[str]] = None) -> List[str]:
    """The customers ``user`` may see *and* whose Exposure page is on, optionally narrowed to ``requested``."""
    accessible = await customer_access_handler.get_user_accessible_customers(user, session)
    query = select(CustomerPortalExposureSettings.customer_code).where(CustomerPortalExposureSettings.enabled.is_(True))
    if "*" not in accessible:
        if not accessible:
            return []
        query = query.where(CustomerPortalExposureSettings.customer_code.in_(accessible))
    if requested:
        query = query.where(CustomerPortalExposureSettings.customer_code.in_(requested))
    return sorted((await session.execute(query)).scalars().all())


async def availability(user: User, session: AsyncSession, customer_code: Optional[str] = None) -> Tuple[Optional[str], bool]:
    """Whether the Exposure page should render: for one customer the caller may see, else for any."""
    if customer_code:
        if not await customer_access_handler.check_customer_access(user, customer_code, session):
            raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")
        settings = await get_exposure_settings(customer_code, session)
        return customer_code, bool(settings and settings.enabled)
    return None, bool(await enabled_customer_codes(user, session))


async def resolve_scope(user: User, session: AsyncSession, requested: Optional[List[str]] = None) -> ExposureScope:
    """The customers and agents a caller's Exposure view covers; empty when the page is off for them."""
    codes = await enabled_customer_codes(user, session, requested)
    if not codes:
        return ExposureScope()
    rows = await session.execute(
        select(Agents.agent_id, Agents.hostname, Agents.customer_code).where(Agents.customer_code.in_(codes)),
    )
    agents = [
        ScopedAgent(agent_id=str(agent_id), hostname=hostname, customer_code=code)
        for agent_id, hostname, code in rows.all()
        if agent_id and hostname
    ]
    return ExposureScope(customer_codes=codes, agents=agents)
