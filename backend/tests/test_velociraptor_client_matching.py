"""Matching Velociraptor clients to agents when hostnames collide across customers (#1195).

Two customers each own an endpoint named `HOST-01`, enrolled in different Velociraptor
orgs (or both in root). Before this fix the sync matched org by org, committing after
each one, and preferred hostname over the stored id, so a hand-set id was overwritten
by whichever org came last.

Pure unit tests: the resolver takes plain lists, and the sync test monkeypatches the
Velociraptor fetches and the database session.

Run with: cd backend && python -m pytest tests/test_velociraptor_client_matching.py
"""

import asyncio
import os
from contextlib import asynccontextmanager
from types import SimpleNamespace

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.agents.services.sync as sync  # noqa: E402
from app.agents.velociraptor.schema.agents import Organization  # noqa: E402
from app.agents.velociraptor.schema.agents import VelociraptorClient  # noqa: E402
from app.agents.velociraptor.schema.agents import VelociraptorClients  # noqa: E402
from app.agents.velociraptor.schema.agents import (  # noqa: E402
    VelociraptorOrganizations,
)
from app.agents.velociraptor.utils.matching import RESOLVED_HOSTNAME  # noqa: E402
from app.agents.velociraptor.utils.matching import RESOLVED_PINNED  # noqa: E402
from app.agents.velociraptor.utils.matching import RESOLVED_STORED_ID  # noqa: E402
from app.agents.velociraptor.utils.matching import (  # noqa: E402
    RESOLVED_STORED_ID_FALLBACK,
)
from app.agents.velociraptor.utils.matching import UNRESOLVED_AMBIGUOUS  # noqa: E402
from app.agents.velociraptor.utils.matching import UNRESOLVED_CONTESTED  # noqa: E402
from app.agents.velociraptor.utils.matching import UNRESOLVED_NO_MATCH  # noqa: E402
from app.agents.velociraptor.utils.matching import (  # noqa: E402
    UNRESOLVED_PINNED_CLIENT_MISSING,
)
from app.agents.velociraptor.utils.matching import AgentRef  # noqa: E402
from app.agents.velociraptor.utils.matching import OrgClient  # noqa: E402
from app.agents.velociraptor.utils.matching import (  # noqa: E402
    resolve_velociraptor_clients,
)

A_CLIENT = "C.aaaaaaaaaaaaaaaa"
B_CLIENT = "C.bbbbbbbbbbbbbbbb"


def make_client(client_id, hostname, last_seen_at=1_700_000_000_000_000):
    return VelociraptorClient(
        client_id=client_id,
        agent_information={"version": "0.75.6", "name": "velociraptor", "build_time": "", "build_url": ""},
        os_info={"system": "windows", "hostname": hostname, "release": "", "machine": "", "fqdn": hostname, "mac_addresses": []},
        first_seen_at=0,
        last_seen_at=last_seen_at,
        last_ip="10.0.0.1",
        last_interrogate_flow_id="",
        last_interrogate_artifact_name="",
        labels=[],
        last_hunt_timestamp=0,
        last_event_table_version=0,
        last_label_timestamp=0,
    )


def org_client(org_id, client_id, hostname):
    return OrgClient(org_id=org_id, client=make_client(client_id, hostname))


def resolve(agents, clients):
    return resolve_velociraptor_clients(agents, clients)


# Customer A's HOST-01 in org OA, customer B's HOST-01 in org OB.
COLLIDING = [org_client("OA", A_CLIENT, "HOST-01"), org_client("OB", B_CLIENT, "HOST-01")]


def test_issue_scenario_both_ids_pinned_survive_in_either_org_order():
    agents = [
        AgentRef(key=1, hostname="HOST-01-A", velociraptor_id=A_CLIENT, pinned=True, customer_code="A"),
        AgentRef(key=2, hostname="HOST-01", velociraptor_id=B_CLIENT, pinned=True, customer_code="B"),
    ]
    for clients in (COLLIDING, list(reversed(COLLIDING))):
        result = resolve(agents, clients)
        assert result[1].client.client_id == A_CLIENT and result[1].reason == RESOLVED_PINNED
        assert result[2].client.client_id == B_CLIENT and result[2].reason == RESOLVED_PINNED
        assert result[2].client.org_id == "OB"


def test_pinned_id_beats_a_hostname_match():
    agents = [AgentRef(key=1, hostname="HOST-01", velociraptor_id=B_CLIENT, pinned=True)]
    clients = [org_client("OA", A_CLIENT, "HOST-01"), org_client("OB", B_CLIENT, "SOMETHING-ELSE")]
    assert resolve(agents, clients)[1].client.client_id == B_CLIENT


def test_one_pinned_agent_lets_the_other_resolve_by_elimination():
    # Only customer A's renamed agent was set by hand; B's row still holds A's client.
    agents = [
        AgentRef(key=1, hostname="HOST-01-A", velociraptor_id=A_CLIENT, pinned=True),
        AgentRef(key=2, hostname="HOST-01", velociraptor_id=A_CLIENT),
    ]
    result = resolve(agents, COLLIDING)
    assert result[1].client.client_id == A_CLIENT
    assert result[2].client.client_id == B_CLIENT and result[2].reason == RESOLVED_HOSTNAME


def test_pinned_client_missing_is_left_unchanged():
    agents = [AgentRef(key=1, hostname="HOST-01", velociraptor_id="C.deadbeefdeadbeef", pinned=True)]
    result = resolve(agents, COLLIDING)
    assert not result[1].resolved and result[1].reason == UNRESOLVED_PINNED_CLIENT_MISSING


def test_shared_hostname_without_ids_is_ambiguous_not_guessed():
    agents = [AgentRef(key=1, hostname="HOST-01", velociraptor_id=None)]
    result = resolve(agents, COLLIDING)
    assert not result[1].resolved and result[1].reason == UNRESOLVED_AMBIGUOUS
    assert len(result[1].candidates) == 2


def test_same_hostname_twice_in_root_is_ambiguous():
    clients = [org_client("root", A_CLIENT, "HOST-01"), org_client("root", B_CLIENT, "HOST-01")]
    agents = [AgentRef(key=1, hostname="HOST-01", velociraptor_id=None)]
    assert resolve(agents, clients)[1].reason == UNRESOLVED_AMBIGUOUS


def test_unpinned_stored_id_with_matching_hostname_is_kept_over_the_other_tenant():
    agents = [AgentRef(key=1, hostname="HOST-01", velociraptor_id=B_CLIENT)]
    for clients in (COLLIDING, list(reversed(COLLIDING))):
        result = resolve(agents, clients)
        assert result[1].client.client_id == B_CLIENT and result[1].reason == RESOLVED_STORED_ID


def test_renamed_agent_keeps_its_stored_id():
    agents = [AgentRef(key=1, hostname="HOST-01-A", velociraptor_id=A_CLIENT)]
    result = resolve(agents, COLLIDING)
    assert result[1].client.client_id == A_CLIENT and result[1].reason == RESOLVED_STORED_ID


def test_stale_stored_id_self_corrects_by_hostname():
    # #1120: the row for VDC01 still holds the client of vDC01 (a different machine).
    clients = [org_client("OA", A_CLIENT, "vDC01"), org_client("OB", B_CLIENT, "VDC01")]
    agents = [AgentRef(key=1, hostname="VDC01", velociraptor_id=A_CLIENT)]
    result = resolve(agents, clients)
    assert result[1].client.client_id == B_CLIENT and result[1].reason == RESOLVED_HOSTNAME


def test_two_unpinned_agents_on_one_client_are_contested():
    agents = [
        AgentRef(key=1, hostname="HOST-01-A", velociraptor_id=A_CLIENT),
        AgentRef(key=2, hostname="HOST-01", velociraptor_id=A_CLIENT),
    ]
    result = resolve(agents, COLLIDING)
    assert result[1].reason == UNRESOLVED_CONTESTED
    assert result[2].reason == UNRESOLVED_CONTESTED


def test_two_pinned_agents_on_one_client_are_contested():
    agents = [
        AgentRef(key=1, hostname="HOST-01-A", velociraptor_id=A_CLIENT, pinned=True),
        AgentRef(key=2, hostname="HOST-01", velociraptor_id=A_CLIENT, pinned=True),
    ]
    result = resolve(agents, COLLIDING)
    assert not result[1].resolved and not result[2].resolved


def test_two_agents_picking_the_same_hostname_client_are_contested():
    clients = [org_client("root", A_CLIENT, "HOST-01")]
    agents = [
        AgentRef(key=1, hostname="HOST-01", velociraptor_id=None),
        AgentRef(key=2, hostname="HOST-01", velociraptor_id=None),
    ]
    result = resolve(agents, clients)
    assert result[1].reason == UNRESOLVED_CONTESTED and result[2].reason == UNRESOLVED_CONTESTED


def test_stored_id_fallback_when_every_hostname_candidate_is_taken():
    clients = [org_client("OA", A_CLIENT, "HOST-01"), org_client("OB", B_CLIENT, "OLD-NAME")]
    agents = [
        AgentRef(key=1, hostname="HOST-01", velociraptor_id=A_CLIENT, pinned=True),
        AgentRef(key=2, hostname="HOST-01", velociraptor_id=B_CLIENT),
    ]
    result = resolve(agents, clients)
    assert result[2].client.client_id == B_CLIENT and result[2].reason == RESOLVED_STORED_ID_FALLBACK


def test_no_client_at_all():
    agents = [AgentRef(key=1, hostname="LONELY", velociraptor_id=None)]
    assert resolve(agents, COLLIDING)[1].reason == UNRESOLVED_NO_MATCH


def test_unique_hostname_still_matches():
    agents = [AgentRef(key=1, hostname="HOST-02", velociraptor_id=None)]
    clients = COLLIDING + [org_client("OB", "C.cccccccccccccccc", "HOST-02")]
    result = resolve(agents, clients)
    assert result[1].client.client_id == "C.cccccccccccccccc" and result[1].client.org_id == "OB"


# --- the sync itself --------------------------------------------------------------------


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, rows):
        self.rows = {row.id: row for row in rows}

    async def execute(self, _query):
        return FakeResult(list(self.rows.values()))

    async def get(self, _model, key):
        return self.rows[key]

    def add(self, _obj):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass


def agent_row(row_id, hostname, velociraptor_id, pinned, customer_code):
    row = SimpleNamespace(
        id=row_id,
        hostname=hostname,
        velociraptor_id=velociraptor_id,
        velociraptor_id_pinned=pinned,
        customer_code=customer_code,
        velociraptor_org=None,
    )

    def update_velociraptor_details(velociraptor_agent):
        row.velociraptor_id = velociraptor_agent.client_id
        row.velociraptor_org = velociraptor_agent.client_org

    row.update_velociraptor_details = update_velociraptor_details
    return row


def run_sync(monkeypatch, rows, clients_by_org):
    session = FakeSession(rows)

    @asynccontextmanager
    async def fake_db_session():
        yield session

    async def fake_verified():
        return True

    async def fake_orgs():
        return VelociraptorOrganizations(organizations=[Organization(Name=org, OrgId=org) for org in clients_by_org])

    async def fake_clients(org_id):
        result = clients_by_org[org_id]
        if isinstance(result, Exception):
            raise result
        return VelociraptorClients(clients=result)

    monkeypatch.setattr(sync, "is_velociraptor_verified", fake_verified)
    monkeypatch.setattr(sync, "fetch_velociraptor_organizations", fake_orgs)
    monkeypatch.setattr(sync, "fetch_velociraptor_clients", fake_clients)
    monkeypatch.setattr(sync, "get_db_session", fake_db_session)
    return asyncio.run(sync.sync_agents_velociraptor())


def test_sync_keeps_both_pinned_ids_whatever_the_org_order(monkeypatch):
    for org_order in (("OA", "OB"), ("OB", "OA")):
        clients = {"OA": [make_client(A_CLIENT, "HOST-01")], "OB": [make_client(B_CLIENT, "HOST-01")]}
        rows = [
            agent_row(1, "HOST-01-A", A_CLIENT, True, "A"),
            agent_row(2, "HOST-01", B_CLIENT, True, "B"),
        ]
        run_sync(monkeypatch, rows, {org: clients[org] for org in org_order})
        assert (rows[0].velociraptor_id, rows[0].velociraptor_org) == (A_CLIENT, "OA")
        assert (rows[1].velociraptor_id, rows[1].velociraptor_org) == (B_CLIENT, "OB")


def test_sync_leaves_an_ambiguous_agent_unchanged_and_says_so(monkeypatch):
    rows = [agent_row(1, "HOST-01", None, False, "B")]
    response = run_sync(
        monkeypatch,
        rows,
        {"OA": [make_client(A_CLIENT, "HOST-01")], "OB": [make_client(B_CLIENT, "HOST-01")]},
    )
    assert rows[0].velociraptor_id is None
    assert "HOST-01" in response.message


def test_sync_skips_the_run_when_one_org_cannot_be_read(monkeypatch):
    # With OB unreadable, HOST-01 would look unique and take customer A's client.
    rows = [agent_row(1, "HOST-01", B_CLIENT, False, "B")]
    response = run_sync(
        monkeypatch,
        rows,
        {"OA": [make_client(A_CLIENT, "HOST-01")], "OB": RuntimeError("org unreachable")},
    )
    assert rows[0].velociraptor_id == B_CLIENT
    assert "Skipped" in response.message
