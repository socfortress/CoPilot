"""SOC Management (#1187) — the lifecycle recorder and the policy service, on a real database.

In-memory SQLite. The recorder is given the test session factory, exactly as production
gives it ``AsyncSessionLocal``: every call runs in a session of its own.

Pinned here:
- opening snapshots the targets in force (customer override > global > default);
- the first SOC response is write-once, whoever comes second;
- a customer never acknowledges; automation never acknowledges;
- close / reopen / close keeps the first resolution and counts the reopen;
- a severity change re-targets only the clocks still running;
- the recorder never raises, even when the item does not exist;
- policy replace/clear semantics and the opt-in re-target of open items.

Run with: cd backend && python -m pytest tests/test_soc_management_lifecycle.py
"""

import asyncio
import os
from datetime import timedelta

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from sqlalchemy import select  # noqa: E402

from app.incidents.models import CaseAlertLink  # noqa: E402
from app.soc_management.domain.lifecycle import Actor  # noqa: E402
from app.soc_management.domain.lifecycle import LifecycleAction  # noqa: E402
from app.soc_management.domain.policy import SlaEntity  # noqa: E402
from app.soc_management.domain.policy import TargetSource  # noqa: E402
from app.soc_management.models.sla import SlaPolicy  # noqa: E402
from app.soc_management.schema.policy import PolicyCellIn  # noqa: E402
from app.soc_management.services import policy as policy_service  # noqa: E402
from app.soc_management.services.lifecycle import SlaLifecycleRecorder  # noqa: E402
from app.soc_management.services.lifecycle import case_effective_severity  # noqa: E402
from app.soc_management.services.lifecycle import retarget_open  # noqa: E402
from tests.soc_management_support import T0  # noqa: E402
from tests.soc_management_support import AlertSlaTracking  # noqa: E402
from tests.soc_management_support import CaseSlaTracking  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402
from tests.soc_management_support import add_case  # noqa: E402

ANA = Actor(username="ana", is_soc=True)
BOB = Actor(username="bob", is_soc=True)
PORTAL = Actor(username="portal-user", is_soc=False)


class Clock:
    """A settable clock, so every milestone lands at a known instant."""

    def __init__(self, now=T0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, delta):
        self.now = self.now + delta
        return self.now


def run(scenario):
    async def _inner():
        db = await Db().create()
        try:
            return await scenario(db)
        finally:
            await db.dispose()

    return asyncio.run(_inner())


async def _tracking(db, model, key):
    async with db.session() as session:
        return await session.get(model, key)


# ── opening ──────────────────────────────────────────────────────────────────


def test_opening_snapshots_the_targets_in_force():
    async def scenario(db):
        clock = Clock()
        async with db.session() as session:
            session.add(SlaPolicy(customer_code=None, entity_type="alert", severity="High", ack_minutes=20, resolve_minutes=120))
            session.add(SlaPolicy(customer_code="ACME", entity_type="alert", severity="High", ack_minutes=5, resolve_minutes=60))
            await session.commit()
            acme = await add_alert(session, customer="ACME")
            globex = await add_alert(session, customer="GLOBEX")
            low = await add_alert(session, customer="GLOBEX", severity="Low")
        recorder = SlaLifecycleRecorder(db.factory, clock=clock)
        for alert in (acme, globex, low):
            await recorder.alert_opened(alert)
        return [await _tracking(db, AlertSlaTracking, a.id) for a in (acme, globex, low)]

    acme, globex, low = run(scenario)
    assert acme.tracked and acme.opened_at == T0
    assert acme.ack_due_at == T0 + timedelta(minutes=5) and acme.resolve_due_at == T0 + timedelta(minutes=60)
    assert globex.ack_due_at == T0 + timedelta(minutes=20)
    assert low.ack_due_at == T0 + timedelta(hours=8)  # built-in Low default
    assert acme.first_ack_at is None  # automation opened it: nobody responded yet


def test_opening_is_idempotent_and_uses_the_effective_severity():
    async def scenario(db):
        async with db.session() as session:
            alert = await add_alert(session, severity=None)
        recorder = SlaLifecycleRecorder(db.factory, clock=Clock())
        await recorder.alert_opened(alert)
        await recorder.alert_opened(alert)
        async with db.session() as session:
            rows = (await session.execute(select(AlertSlaTracking))).scalars().all()
        return rows

    rows = run(scenario)
    assert len(rows) == 1
    assert rows[0].severity == "High"  # NULL severity resolves to the deployment default


# ── acknowledgement ──────────────────────────────────────────────────────────


def test_the_first_soc_response_is_write_once():
    async def scenario(db):
        clock = Clock()
        async with db.session() as session:
            alert = await add_alert(session)
        recorder = SlaLifecycleRecorder(db.factory, clock=clock)
        await recorder.alert_opened(alert)
        clock.advance(timedelta(minutes=12))
        await recorder.alert_action(alert.id, LifecycleAction.ASSIGNED, ANA, assignee="ana")
        clock.advance(timedelta(minutes=30))
        await recorder.alert_action(alert.id, LifecycleAction.COMMENTED, BOB)
        await recorder.alert_action(alert.id, LifecycleAction.ASSIGNED, BOB, assignee="bob")
        return await _tracking(db, AlertSlaTracking, alert.id)

    row = run(scenario)
    assert row.first_ack_at == T0 + timedelta(minutes=12)
    assert (row.first_ack_by, row.first_ack_action) == ("ana", "assigned")
    assert row.first_assigned_at == T0 + timedelta(minutes=12)


def test_a_customer_comment_does_not_acknowledge():
    async def scenario(db):
        async with db.session() as session:
            alert = await add_alert(session)
        recorder = SlaLifecycleRecorder(db.factory, clock=Clock())
        await recorder.alert_opened(alert)
        await recorder.alert_action(alert.id, LifecycleAction.COMMENTED, PORTAL)
        return await _tracking(db, AlertSlaTracking, alert.id)

    assert run(scenario).first_ack_at is None


# ── resolution ───────────────────────────────────────────────────────────────


def test_close_reopen_close_keeps_the_first_resolution_and_counts_the_reopen():
    async def scenario(db):
        clock = Clock()
        async with db.session() as session:
            alert = await add_alert(session)
        recorder = SlaLifecycleRecorder(db.factory, clock=clock)
        await recorder.alert_opened(alert)
        clock.advance(timedelta(hours=1))
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, ANA, to_status="CLOSED")
        after_close = await _tracking(db, AlertSlaTracking, alert.id)
        clock.advance(timedelta(hours=1))
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, BOB, to_status="IN_PROGRESS")
        after_reopen = await _tracking(db, AlertSlaTracking, alert.id)
        clock.advance(timedelta(hours=1))
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, BOB, to_status="CLOSED")
        # A second close of an already-closed item changes nothing.
        clock.advance(timedelta(hours=1))
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, ANA, to_status="CLOSED")
        return after_close, after_reopen, await _tracking(db, AlertSlaTracking, alert.id)

    after_close, after_reopen, final = run(scenario)
    assert after_close.resolved_at == T0 + timedelta(hours=1) and after_close.resolved_by == "ana"
    assert after_reopen.resolved_at is None and after_reopen.reopen_count == 1
    assert final.resolved_at == T0 + timedelta(hours=3) and final.resolved_by == "bob"
    assert final.first_resolved_at == T0 + timedelta(hours=1)
    assert final.reopen_count == 1
    assert final.first_ack_by == "ana"  # the first close was also the first response


def test_reopening_an_open_item_is_not_a_reopen():
    async def scenario(db):
        async with db.session() as session:
            alert = await add_alert(session)
        recorder = SlaLifecycleRecorder(db.factory, clock=Clock())
        await recorder.alert_opened(alert)
        await recorder.alert_action(alert.id, LifecycleAction.STATUS_CHANGED, ANA, to_status="IN_PROGRESS")
        return await _tracking(db, AlertSlaTracking, alert.id)

    assert run(scenario).reopen_count == 0


# ── robustness ───────────────────────────────────────────────────────────────


def test_the_recorder_never_raises_and_creates_untracked_rows_for_unknown_items():
    async def scenario(db):
        async with db.session() as session:
            alert = await add_alert(session)  # no opening recorded: as for an item created by a forgotten path
        recorder = SlaLifecycleRecorder(db.factory, clock=Clock(T0 + timedelta(hours=2)))
        await recorder.alert_action(999, LifecycleAction.COMMENTED, ANA)  # does not exist: logged, not raised
        await recorder.alert_action(alert.id, LifecycleAction.COMMENTED, ANA)
        return await _tracking(db, AlertSlaTracking, alert.id)

    row = run(scenario)
    assert row.tracked is False  # its opening was never observed
    assert row.first_ack_by == "ana"  # but the action is kept


def test_a_broken_session_factory_is_swallowed():
    def broken():
        raise RuntimeError("database unreachable")

    async def scenario(db):
        async with db.session() as session:
            alert = await add_alert(session)
        recorder = SlaLifecycleRecorder(broken, clock=Clock())
        await recorder.alert_opened(alert)
        await recorder.alert_action(alert.id, LifecycleAction.ASSIGNED, ANA, assignee="ana")
        return True

    assert run(scenario) is True


# ── cases ────────────────────────────────────────────────────────────────────


def test_case_severity_follows_its_most_severe_alert_unless_set():
    async def scenario(db):
        async with db.session() as session:
            case = await add_case(session)
            low = await add_alert(session, severity="Low")
            critical = await add_alert(session, severity="Critical")
            session.add_all([CaseAlertLink(case_id=case.id, alert_id=low.id), CaseAlertLink(case_id=case.id, alert_id=critical.id)])
            await session.commit()
            derived = await case_effective_severity(session, case)
            case.severity = "Medium"
            explicit = await case_effective_severity(session, case)
            lonely = await case_effective_severity(session, await add_case(session))
        return derived, explicit, lonely

    assert run(scenario) == ("Critical", "Medium", "High")


def test_case_retarget_moves_only_running_clocks():
    async def scenario(db):
        clock = Clock()
        async with db.session() as session:
            case = await add_case(session)  # no links → default High → 1h ack, 3d resolve
        recorder = SlaLifecycleRecorder(db.factory, clock=clock)
        await recorder.case_opened(case)
        opened = await _tracking(db, CaseSlaTracking, case.id)
        clock.advance(timedelta(minutes=50))
        await recorder.case_action(case.id, LifecycleAction.COMMENTED, ANA)  # on-time High acknowledgement
        async with db.session() as session:
            stored = await session.get(type(case), case.id)
            stored.severity = "Critical"
            await session.commit()
        clock.advance(timedelta(minutes=5))
        await recorder.case_severity_changed(case.id, BOB)
        return opened, await _tracking(db, CaseSlaTracking, case.id)

    opened, row = run(scenario)
    assert opened.severity == "High" and opened.ack_due_at == T0 + timedelta(hours=1)
    assert row.severity == "Critical"
    assert row.ack_due_at == T0 + timedelta(hours=1)  # already achieved: judged against High, unchanged
    assert row.resolve_due_at == T0 + timedelta(days=1)  # still running: now Critical's 24h
    assert row.first_ack_by == "ana"


def test_linking_a_critical_alert_retargets_a_derived_case():
    async def scenario(db):
        async with db.session() as session:
            case = await add_case(session)
            critical = await add_alert(session, severity="Critical")
        recorder = SlaLifecycleRecorder(db.factory, clock=Clock())
        await recorder.case_opened(case)
        async with db.session() as session:
            session.add(CaseAlertLink(case_id=case.id, alert_id=critical.id))
            await session.commit()
        await recorder.case_links_changed(case.id)
        return await _tracking(db, CaseSlaTracking, case.id)

    row = run(scenario)
    assert row.severity == "Critical" and row.ack_due_at == T0 + timedelta(minutes=30)


# ── policy service ───────────────────────────────────────────────────────────


def _cell(entity, severity, ack=None, resolve=None, inherit=False):
    return PolicyCellIn(entity=entity, severity=severity, ack_minutes=ack, resolve_minutes=resolve, inherit=inherit)


def test_replace_scope_stores_exactly_the_non_inheriting_cells():
    async def scenario(db):
        async with db.session() as session:
            await policy_service.replace_scope(session, None, [_cell("alert", "High", 10, 100), _cell("case", "Low", 60, 600)], "admin")
            await session.commit()
            matrix = await policy_service.replace_scope(
                session,
                None,
                [_cell("alert", "High", 15, 150), _cell("case", "Low", inherit=True)],
                "admin",
            )
            await session.commit()
            stored = (await session.execute(select(SlaPolicy))).scalars().all()
        return matrix, stored

    matrix, stored = run(scenario)
    assert [(row.entity_type, row.severity, row.ack_minutes) for row in stored] == [("alert", "High", 15)]
    cells = {(cell.entity, cell.severity): cell for cell in matrix.cells}
    assert cells[(SlaEntity.ALERT, "High")].source is TargetSource.GLOBAL
    assert cells[(SlaEntity.CASE, "Low")].source is TargetSource.DEFAULT
    assert len(matrix.cells) == 10


def test_customer_overrides_are_listed_and_cleared():
    async def scenario(db):
        async with db.session() as session:
            await policy_service.replace_scope(session, "ACME", [_cell("alert", "High", 5, 50), _cell("alert", "Low", 50, 500)], "admin")
            await policy_service.replace_scope(session, "GLOBEX", [_cell("case", "High", 5, 50)], "admin")
            await session.commit()
            overrides = await policy_service.list_overrides(session)
            scoped = await policy_service.list_overrides(session, ["GLOBEX"])
            removed = await policy_service.clear_scope(session, "ACME")
            await session.commit()
            after = await policy_service.get_matrix(session, "ACME")
        return overrides, scoped, removed, after

    overrides, scoped, removed, after = run(scenario)
    assert [(o.customer_code, o.cells) for o in overrides] == [("ACME", 2), ("GLOBEX", 1)]
    assert [o.customer_code for o in scoped] == ["GLOBEX"]
    assert removed == 2
    assert all(cell.source is TargetSource.DEFAULT for cell in after.cells)


def test_retarget_open_applies_a_new_policy_to_running_clocks_only():
    async def scenario(db):
        clock = Clock()
        async with db.session() as session:
            running = await add_alert(session, customer="ACME")
            acked = await add_alert(session, customer="ACME")
            closed = await add_alert(session, customer="ACME")
            other = await add_alert(session, customer="GLOBEX")
        recorder = SlaLifecycleRecorder(db.factory, clock=clock)
        for alert in (running, acked, closed, other):
            await recorder.alert_opened(alert)
        await recorder.alert_action(acked.id, LifecycleAction.COMMENTED, ANA)
        await recorder.alert_action(closed.id, LifecycleAction.STATUS_CHANGED, ANA, to_status="CLOSED")

        async with db.session() as session:
            await policy_service.replace_scope(session, "ACME", [_cell("alert", "High", 10, 30)], "admin")
            moved = await retarget_open(session, "ACME", now=clock())
            await session.commit()
        rows = [await _tracking(db, AlertSlaTracking, a.id) for a in (running, acked, closed, other)]
        return moved, rows

    moved, (running, acked, closed, other) = run(scenario)
    assert moved == 2  # running (both clocks) and acked (resolve only)
    assert running.ack_due_at == T0 + timedelta(minutes=10) and running.resolve_due_at == T0 + timedelta(minutes=30)
    assert acked.ack_due_at == T0 + timedelta(hours=1) and acked.resolve_due_at == T0 + timedelta(minutes=30)
    assert closed.resolve_due_at == T0 + timedelta(hours=8)  # decided: never rewritten
    assert other.ack_due_at == T0 + timedelta(hours=1)  # another customer's scope
