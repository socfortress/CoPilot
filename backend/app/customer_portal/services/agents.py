"""The Customer Portal agents list, paginated, filtered and counted in SQL.

The portal used to download every agent the user can see and filter, count and
paginate them in the browser — megabytes for a fleet of thousands, and a re-filter of
the whole list on every keystroke. Everything here happens in the database; the
browser receives one page plus the numbers it displays.
"""

import csv
import io
from dataclasses import dataclass
from typing import List
from typing import Optional

from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.customer_portal.schema.agents import PortalAgentStats
from app.db.universal_models import Agents
from app.middleware.customer_access import customer_access_handler

# Wazuh statuses the portal counts as "offline" in its cards.
OFFLINE_STATUSES = ("disconnected", "never_connected")


@dataclass
class AgentFilters:
    search: Optional[str] = None
    status: Optional[str] = None
    os: Optional[str] = None
    critical: bool = False


@dataclass
class AgentsPage:
    agents: list
    total: int
    stats: PortalAgentStats
    statuses: List[str]
    os_list: List[str]


async def _scope(user: User, session: AsyncSession, customer_codes: Optional[List[str]]) -> Optional[list]:
    """WHERE clauses for the agents ``user`` may see; None when that is none at all."""
    customers = await customer_access_handler.resolve_effective_customers(user, customer_codes, session)
    if "*" in customers:
        return []
    return [Agents.customer_code.in_(customers)] if customers else None


def _filter_clauses(filters: AgentFilters) -> list:
    clauses = []
    if filters.search:
        term = f"%{filters.search.strip()}%"
        clauses.append(or_(Agents.hostname.ilike(term), Agents.ip_address.ilike(term), Agents.agent_id.ilike(term)))
    if filters.status:
        clauses.append(Agents.wazuh_agent_status == filters.status)
    if filters.os:
        clauses.append(Agents.os == filters.os)
    if filters.critical:
        clauses.append(Agents.critical_asset.is_(True))
    return clauses


async def list_portal_agents(
    user: User,
    session: AsyncSession,
    filters: AgentFilters,
    page: int,
    page_size: int,
    customer_codes: Optional[List[str]] = None,
) -> AgentsPage:
    scope = await _scope(user, session, customer_codes)
    if scope is None:
        return AgentsPage(agents=[], total=0, stats=PortalAgentStats(), statuses=[], os_list=[])

    where = [*scope, *_filter_clauses(filters)]
    total = (await session.execute(select(func.count(Agents.id)).where(*where))).scalar_one()
    agents = (
        (await session.execute(select(Agents).where(*where).order_by(Agents.id).offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )

    # Cards and filter options describe the whole scope, not the filtered list.
    count, active, critical, offline = (
        await session.execute(
            select(
                func.count(Agents.id),
                func.coalesce(func.sum(case((Agents.wazuh_agent_status == "active", 1), else_=0)), 0),
                func.coalesce(func.sum(case((Agents.critical_asset.is_(True), 1), else_=0)), 0),
                func.coalesce(func.sum(case((Agents.wazuh_agent_status.in_(OFFLINE_STATUSES), 1), else_=0)), 0),
            ).where(*scope),
        )
    ).one()
    statuses = (
        (await session.execute(select(Agents.wazuh_agent_status).where(*scope).distinct().order_by(Agents.wazuh_agent_status)))
        .scalars()
        .all()
    )
    os_list = (await session.execute(select(Agents.os).where(*scope).distinct().order_by(Agents.os))).scalars().all()

    return AgentsPage(
        agents=list(agents),
        total=total,
        stats=PortalAgentStats(total=count, active=active, critical=critical, offline=offline),
        statuses=[value for value in statuses if value],
        os_list=[value for value in os_list if value],
    )


CSV_HEADERS = [
    "Hostname",
    "Agent ID",
    "IP Address",
    "Operating System",
    "Status",
    "Last Seen",
    "Critical Asset",
    "Agent Version",
    "Customer Code",
]


async def export_portal_agents_csv(
    user: User,
    session: AsyncSession,
    filters: AgentFilters,
    customer_codes: Optional[List[str]] = None,
) -> str:
    """Every agent matching the filters (not just one page), as CSV. Timestamps are ISO 8601 UTC."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADERS)

    scope = await _scope(user, session, customer_codes)
    if scope is not None:
        rows = (await session.execute(select(Agents).where(*scope, *_filter_clauses(filters)).order_by(Agents.id))).scalars()
        for agent in rows:
            writer.writerow(
                [
                    agent.hostname,
                    agent.agent_id,
                    agent.ip_address,
                    agent.os,
                    agent.wazuh_agent_status,
                    agent.wazuh_last_seen.isoformat() if agent.wazuh_last_seen else "",
                    "Yes" if agent.critical_asset else "No",
                    agent.wazuh_agent_version,
                    agent.customer_code,
                ],
            )
    return buffer.getvalue()
