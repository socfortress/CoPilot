"""The sidebar serves deployment-wide indicators from memory (#1072).

Twelve of the fourteen indicators give the same answer for every user. Computing
them per request is what kept `/status/sidebar` at ~3s even after they were
parallelised — a dozen database round-trips contending for connections. They are
now assembled by a scheduled job; only the two genuinely per-user indicators
(whose alerts, whose cases) are still computed live.

The risky part of that change is not the caching, it is the **role gating**: it
used to be expressed by which builders were added to the list, and is now a
filter applied to a shared cache. A mistake there would show an admin-only
indicator to a customer user, which these tests exist to prevent.

Run with: cd backend && python -m pytest tests/test_sidebar_shared_indicators.py
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.auth.models.users import RoleEnum  # noqa: E402
from app.status.schema.context import SidebarHealthIndicator  # noqa: E402
from app.status.services import context as context_module  # noqa: E402


def _ind(name):
    """A real indicator: the response model validates these, stubs will not."""
    return SidebarHealthIndicator(id=name, status="ok", label=name, detail="", count=0, category="operations")


def _session():
    return MagicMock(spec=AsyncSession)


def _user(role):
    return SimpleNamespace(role_id=role.value)


@pytest.fixture(autouse=True)
def _isolated_cache(monkeypatch):
    """Every test starts from a cold shared cache and a stubbed session factory."""
    context_module._shared_indicators = None
    context_module._shared_indicators_at = None
    context_module._shared_audiences = []

    @asynccontextmanager
    async def fake_get_db_session():
        yield _session()

    monkeypatch.setattr(context_module, "get_db_session", fake_get_db_session)
    # The version check is an outbound GitHub call; not what these tests are about.
    monkeypatch.setattr(
        context_module,
        "_get_version_fields",
        lambda: asyncio.sleep(0, result={"current_version": "0.0.0", "latest_version": None, "is_outdated": False}),
    )
    yield
    context_module._shared_indicators = None
    context_module._shared_indicators_at = None
    context_module._shared_audiences = []


def _prime_cache(pairs):
    """Populate the shared cache with (indicator_id, audience) pairs."""
    context_module._shared_indicators = [_ind(name) for name, _ in pairs]
    context_module._shared_audiences = [audience for _, audience in pairs]
    context_module._shared_indicators_at = datetime.utcnow()


def _build(user, monkeypatch, personal=("open_alerts", "my_cases")):
    """Run build_sidebar_context with the per-user builders stubbed out."""

    async def fake_gather(builders):
        return [_ind(name) for name in personal] if builders else []

    monkeypatch.setattr(context_module, "_gather_indicators", fake_gather)
    monkeypatch.setattr(context_module, "_schedule_shared_refresh", lambda: None)

    response = asyncio.run(context_module.build_sidebar_context(session=_session(), user=user))
    return [indicator.id for indicator in response.indicators]


# ── role gating ─────────────────────────────────────────────────────────────


def test_admin_sees_analyst_and_admin_indicators(monkeypatch):
    _prime_cache([("catalog", {"analyst", "customer"}), ("licence", {"admin"}), ("scheduler", {"analyst"})])

    ids = _build(_user(RoleEnum.admin), monkeypatch)

    assert set(ids) == {"open_alerts", "my_cases", "catalog", "licence", "scheduler"}


def test_analyst_never_sees_admin_only_indicators(monkeypatch):
    _prime_cache([("catalog", {"analyst", "customer"}), ("licence", {"admin"}), ("scheduler", {"analyst"})])

    ids = _build(_user(RoleEnum.analyst), monkeypatch)

    assert "licence" not in ids, "an analyst must not see admin-only indicators"
    assert {"catalog", "scheduler"} <= set(ids)


def test_customer_user_sees_only_their_slice(monkeypatch):
    _prime_cache([("catalog", {"analyst", "customer"}), ("licence", {"admin"}), ("scheduler", {"analyst"})])

    ids = _build(_user(RoleEnum.customer_user), monkeypatch)

    assert "catalog" in ids
    assert "scheduler" not in ids, "a customer user must not see analyst indicators"
    assert "licence" not in ids, "a customer user must not see admin indicators"


def test_personal_indicators_come_first_and_in_order(monkeypatch):
    """The sidebar renders in list order; the split must not reshuffle it."""
    _prime_cache([("catalog", {"analyst"}), ("scheduler", {"analyst"})])

    ids = _build(_user(RoleEnum.analyst), monkeypatch)

    assert ids == ["open_alerts", "my_cases", "catalog", "scheduler"]


# ── the cache itself ────────────────────────────────────────────────────────


def test_a_cold_cache_still_serves_the_personal_indicators(monkeypatch):
    """A restart must not produce an error page, just a thinner sidebar."""
    scheduled = []
    monkeypatch.setattr(context_module, "_schedule_shared_refresh", lambda: scheduled.append(True))

    async def fake_gather(builders):
        return [_ind("open_alerts")] if builders else []

    monkeypatch.setattr(context_module, "_gather_indicators", fake_gather)

    response = asyncio.run(context_module.build_sidebar_context(session=_session(), user=_user(RoleEnum.admin)))

    assert [i.id for i in response.indicators] == ["open_alerts"]
    assert scheduled == [True], "a cold cache must trigger a background refresh"


def test_a_stale_cache_is_served_and_refreshed(monkeypatch):
    """Serving slightly stale health beats making the user wait for fresh health."""
    _prime_cache([("catalog", {"analyst"})])
    context_module._shared_indicators_at = datetime.utcnow() - timedelta(
        seconds=context_module.SHARED_INDICATORS_TTL_SECONDS + 1,
    )

    scheduled = []
    monkeypatch.setattr(context_module, "_schedule_shared_refresh", lambda: scheduled.append(True))

    async def fake_gather(builders):
        return []

    monkeypatch.setattr(context_module, "_gather_indicators", fake_gather)

    response = asyncio.run(context_module.build_sidebar_context(session=_session(), user=_user(RoleEnum.analyst)))

    assert [i.id for i in response.indicators] == ["catalog"], "the stale value should still be served"
    assert scheduled == [True], "and a refresh should have been kicked off"


def test_a_fresh_cache_triggers_no_refresh(monkeypatch):
    _prime_cache([("catalog", {"analyst"})])

    scheduled = []
    monkeypatch.setattr(context_module, "_schedule_shared_refresh", lambda: scheduled.append(True))

    async def fake_gather(builders):
        return []

    monkeypatch.setattr(context_module, "_gather_indicators", fake_gather)

    asyncio.run(context_module.build_sidebar_context(session=_session(), user=_user(RoleEnum.analyst)))

    assert scheduled == [], "a fresh cache must not schedule work"


def test_the_request_path_builds_only_the_per_user_indicators(monkeypatch):
    """The whole point: fourteen builders per request became two."""
    _prime_cache([("catalog", {"analyst"}), ("scheduler", {"analyst"})])
    built = []

    async def fake_gather(builders):
        built.extend(builder.__name__ for builder, _, _ in builders)
        return []

    monkeypatch.setattr(context_module, "_gather_indicators", fake_gather)
    monkeypatch.setattr(context_module, "_schedule_shared_refresh", lambda: None)

    asyncio.run(context_module.build_sidebar_context(session=_session(), user=_user(RoleEnum.admin)))

    assert built == ["build_open_alerts_indicator", "build_my_open_cases_indicator"]


def test_refresh_computes_every_shared_builder(monkeypatch):
    """The job must cover all of them, and record each one's audience."""
    calls = []

    async def fake_safe_build(builder, *args, **kwargs):
        calls.append(builder.__name__)
        return _ind(builder.__name__)

    monkeypatch.setattr(context_module, "safe_build", fake_safe_build)

    asyncio.run(context_module.refresh_shared_indicators())

    expected = [builder.__name__ for builder, _, _ in context_module._SHARED_BUILDERS]
    assert sorted(calls) == sorted(expected)
    assert len(context_module._shared_audiences) == len(expected)
    assert context_module._shared_indicators_are_fresh()


def test_concurrent_refreshes_run_once(monkeypatch):
    """The scheduled job and a cold-read trigger must not both do the work."""
    calls = 0

    async def fake_safe_build(builder, *args, **kwargs):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return _ind(builder.__name__)

    monkeypatch.setattr(context_module, "safe_build", fake_safe_build)

    async def scenario():
        await asyncio.gather(*[context_module.refresh_shared_indicators() for _ in range(4)])

    asyncio.run(scenario())

    assert calls == len(context_module._SHARED_BUILDERS), f"builders ran {calls} times"


# The audiences below are the role gating as it was expressed in the original
# build_sidebar_context, before it moved into _SHARED_BUILDERS:
#
#   is_analyst_or_admin -> tag_rbac, ai_analyst_jobs, mem_palace,
#                          notification_dispatch, scheduler, agent_sync, talon,
#                          core_soc_tools, wazuh_indexer, wazuh_catalog, influx
#   is_customer_user    -> wazuh_catalog only
#   is_admin            -> connector, license, platform_storage (plus the above)
#
# Transcribing that by hand is the part of this refactor most likely to be wrong,
# and a mistake would leak an admin-only indicator to another role. Asserted here
# against the real declarations rather than against synthetic fixtures.
EXPECTED_AUDIENCES = {
    "build_tag_rbac_indicator": {"analyst"},
    "build_ai_analyst_jobs_indicator": {"analyst"},
    "build_mem_palace_indicator": {"analyst"},
    "build_notification_dispatch_indicator": {"analyst"},
    "build_scheduler_indicator_excluding_agent_sync": {"analyst"},
    "build_agent_sync_indicator": {"analyst"},
    "build_talon_indicator": {"analyst"},
    "build_core_soc_tools_indicator": {"analyst"},
    "build_wazuh_indexer_indicator": {"analyst"},
    "_build_wazuh_catalog_indicator": {"analyst", "customer"},
    "build_influx_health_indicator": {"analyst"},
    "_build_connector_indicator": {"admin"},
    "build_license_indicator": {"admin"},
    "build_platform_storage_indicator": {"admin"},
}


def test_declared_audiences_match_the_original_role_gating():
    """Catches a mis-transcribed role, which the filter tests cannot see."""
    declared = {builder.__name__: audience for builder, _, audience in context_module._SHARED_BUILDERS}

    assert declared == EXPECTED_AUDIENCES


def test_no_shared_builder_takes_the_user():
    """A user-dependent builder in the shared cache would leak one user's data.

    The two per-user indicators must stay on the request path; if one were moved
    into _SHARED_BUILDERS, every user would be served whoever refreshed it last.
    """
    import inspect

    for builder, _, _ in context_module._SHARED_BUILDERS:
        parameters = list(inspect.signature(builder).parameters)
        assert "user" not in parameters, f"{builder.__name__} is per-user and cannot be shared"


def test_every_shared_builder_declares_an_audience():
    """A builder with no audience would be computed and then never shown."""
    for builder, _, audience in context_module._SHARED_BUILDERS:
        assert audience, f"{builder.__name__} has no audience and would be invisible"
        assert audience <= {"analyst", "customer", "admin"}, f"{builder.__name__} has an unknown audience"
