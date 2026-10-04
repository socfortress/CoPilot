"""Decide which Velociraptor client belongs to which CoPilot agent (#1195).

Pure: no database, no Velociraptor calls. `sync_agents_velociraptor` collects every
org's clients and every agent row first and hands both lists here, so the answer
no longer depends on the order Velociraptor lists its orgs. Resolving org by org
and committing after each one is what let the last org processed win.

Hostname is not an identity. Two customers can each own a `HOST-01`, and nothing
in CoPilot maps a customer to a Velociraptor org, so a hostname shared by several
clients cannot be settled by looking at the hostname. What can settle it is that a
client belongs to at most one agent: once an agent holds a client through its
pinned or stored id, that client drops out of every other agent's candidates.

A wrong match is worse than no match. Collections, commands and quarantine all act
on the stored id, so guessing hands an analyst another tenant's machine. Anything
ambiguous is left unresolved and the agent keeps the id it already has.

Order of precedence:

1. **Pinned** — an id set by hand (`velociraptor_id_pinned`) resolves by client id
   only, never by hostname. A pinned client that no longer exists is left alone.
2. **Stored id** — an unpinned stored id is kept while its client exists and either
   reports the agent's hostname or no client reports it at all (an agent renamed
   in Wazuh). A stored client with a different hostname while another client does
   carry the agent's hostname is treated as stale, which is how the #1120 mix-up
   still self-corrects.
3. **Hostname** — exactly one unclaimed client with the agent's hostname.
4. **Stored-id fallback** — the stored client, when every hostname candidate is
   already held by another agent.

Two agents claiming the same client at the same step resolve neither.
"""

from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence

from app.agents.velociraptor.schema.agents import VelociraptorClient

RESOLVED_PINNED = "pinned"
RESOLVED_STORED_ID = "stored_id"
RESOLVED_HOSTNAME = "hostname"
RESOLVED_STORED_ID_FALLBACK = "stored_id_fallback"

UNRESOLVED_PINNED_CLIENT_MISSING = "pinned_client_missing"
UNRESOLVED_AMBIGUOUS = "ambiguous"
UNRESOLVED_CONTESTED = "contested"
UNRESOLVED_NO_MATCH = "no_match"


@dataclass(frozen=True)
class OrgClient:
    """A Velociraptor client together with the org it was listed in."""

    org_id: str
    client: VelociraptorClient

    @property
    def client_id(self) -> str:
        return self.client.client_id

    @property
    def hostname(self) -> str:
        return self.client.os_info.hostname


@dataclass(frozen=True)
class AgentRef:
    """The fields of an `agents` row the matching reads."""

    key: int
    hostname: str
    velociraptor_id: Optional[str]
    pinned: bool = False
    customer_code: Optional[str] = None


@dataclass
class Resolution:
    """The outcome for one agent. `client` is None when the agent must be left as it is."""

    reason: str
    client: Optional[OrgClient] = None
    candidates: List[str] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return self.client is not None


def resolve_velociraptor_clients(
    agents: Sequence[AgentRef],
    clients: Sequence[OrgClient],
) -> Dict[int, Resolution]:
    """Return a `Resolution` for every agent, keyed by `AgentRef.key`."""
    by_id: Dict[str, OrgClient] = {}
    by_hostname: Dict[str, List[OrgClient]] = defaultdict(list)
    for org_client in clients:
        by_id.setdefault(org_client.client_id, org_client)
        if org_client.hostname:
            by_hostname[org_client.hostname].append(org_client)

    results: Dict[int, Resolution] = {}
    # Clients no other agent may take: held by a resolved agent, or contested.
    claimed: set = set()

    def settle(claims: Dict[str, List[AgentRef]], reason: str) -> None:
        for client_id, owners in claims.items():
            claimed.add(client_id)
            if len(owners) == 1:
                results[owners[0].key] = Resolution(reason=reason, client=by_id[client_id])
            else:
                for owner in owners:
                    results[owner.key] = Resolution(reason=UNRESOLVED_CONTESTED, candidates=[client_id])

    # 1. Pinned ids.
    pinned_claims: Dict[str, List[AgentRef]] = defaultdict(list)
    for agent in agents:
        if not agent.pinned:
            continue
        if agent.velociraptor_id in by_id:
            pinned_claims[agent.velociraptor_id].append(agent)
        else:
            results[agent.key] = Resolution(reason=UNRESOLVED_PINNED_CLIENT_MISSING)
    settle(pinned_claims, RESOLVED_PINNED)

    # 2. Unpinned stored ids that are still trustworthy.
    stored_claims: Dict[str, List[AgentRef]] = defaultdict(list)
    for agent in agents:
        if agent.key in results or not agent.velociraptor_id:
            continue
        stored = by_id.get(agent.velociraptor_id)
        if stored is None or stored.client_id in claimed:
            continue
        if stored.hostname == agent.hostname or not by_hostname.get(agent.hostname):
            stored_claims[stored.client_id].append(agent)
    settle(stored_claims, RESOLVED_STORED_ID)

    # 3 + 4. Hostname, then the stored id as a last resort.
    picks: Dict[str, List[AgentRef]] = defaultdict(list)
    pick_reasons: Dict[int, str] = {}
    for agent in agents:
        if agent.key in results:
            continue
        candidates = [c for c in by_hostname.get(agent.hostname, []) if c.client_id not in claimed]
        if len(candidates) == 1:
            picks[candidates[0].client_id].append(agent)
            pick_reasons[agent.key] = RESOLVED_HOSTNAME
        elif len(candidates) > 1:
            results[agent.key] = Resolution(
                reason=UNRESOLVED_AMBIGUOUS,
                candidates=[f"{c.client_id} (org {c.org_id})" for c in candidates],
            )
        else:
            stored = by_id.get(agent.velociraptor_id) if agent.velociraptor_id else None
            if stored is not None and stored.client_id not in claimed:
                picks[stored.client_id].append(agent)
                pick_reasons[agent.key] = RESOLVED_STORED_ID_FALLBACK
            else:
                results[agent.key] = Resolution(reason=UNRESOLVED_NO_MATCH)

    for client_id, owners in picks.items():
        if len(owners) == 1:
            results[owners[0].key] = Resolution(reason=pick_reasons[owners[0].key], client=by_id[client_id])
        else:
            for owner in owners:
                results[owner.key] = Resolution(reason=UNRESOLVED_CONTESTED, candidates=[client_id])

    return results
