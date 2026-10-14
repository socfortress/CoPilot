"""The agent vulnerabilities CSV and its EPSS column (#1256).

The export asked the EPSS API about one CVE at a time, in sequence, and a single failed
lookup turned the whole export into a 500. The scores are now looked up in batches of
100 and best-effort: an unreachable EPSS leaves the column empty and the CSV still
comes out. The Customer Portal offers this export to customers.

No network: the EPSS API is an httpx MockTransport.

Run with: cd backend && python -m pytest tests/test_vulnerabilities_csv_epss.py
"""

import asyncio
import csv
import io
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import httpx

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.agents.routes.agents as agent_routes  # noqa: E402
import app.threat_intel.services.epss as epss  # noqa: E402
from app.agents.wazuh.schema.agents import VulnSeverity  # noqa: E402
from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilities  # noqa: E402
from app.agents.wazuh.schema.agents import (  # noqa: E402
    WazuhAgentVulnerabilitiesResponse,
)


def _epss_api(handler):
    """Patch the module's AsyncClient so every request goes to ``handler``."""
    real = httpx.AsyncClient
    return patch.object(epss.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def _scores_for(cves):
    return [{"cve": cve, "epss": f"0.{len(cve)}", "percentile": "0.5", "date": "2026-10-14"} for cve in cves]


def test_one_request_per_hundred_cves_not_one_per_cve():
    requests = []

    def handler(request):
        asked = request.url.params["cve"].split(",")
        requests.append(asked)
        assert request.url.params["limit"] == "100"
        return httpx.Response(200, json={"status-code": 200, "data": _scores_for(asked)})

    cves = [f"CVE-2026-{n:05d}" for n in range(250)]
    with _epss_api(handler):
        scores = asyncio.run(epss.collect_epss_scores(cves))

    assert [len(batch) for batch in requests] == [100, 100, 50]
    assert len(scores) == 250


def test_duplicates_and_blank_cves_are_asked_once_or_not_at_all():
    requests = []

    def handler(request):
        requests.append(request.url.params["cve"])
        return httpx.Response(200, json={"data": _scores_for(request.url.params["cve"].split(","))})

    with _epss_api(handler):
        scores = asyncio.run(epss.collect_epss_scores(["CVE-1", "CVE-1", None, "", "CVE-2"]))

    assert requests == ["CVE-1,CVE-2"]
    assert set(scores) == {"CVE-1", "CVE-2"}


def test_no_cves_no_request():
    with _epss_api(lambda request: (_ for _ in ()).throw(AssertionError("asked EPSS for nothing"))):
        assert asyncio.run(epss.collect_epss_scores([])) == {}


def test_a_failing_batch_is_skipped_and_the_others_kept():
    def handler(request):
        asked = request.url.params["cve"].split(",")
        if "CVE-2026-00000" in asked:
            return httpx.Response(503, text="unavailable")
        return httpx.Response(200, json={"data": _scores_for(asked)})

    cves = [f"CVE-2026-{n:05d}" for n in range(150)]
    with _epss_api(handler):
        scores = asyncio.run(epss.collect_epss_scores(cves))

    assert len(scores) == 50  # the second batch only


def test_an_unreachable_epss_gives_no_scores_rather_than_an_error():
    def handler(request):
        raise httpx.ConnectError("no route to api.first.org", request=request)

    with _epss_api(handler):
        assert asyncio.run(epss.collect_epss_scores(["CVE-1"])) == {}


# ── the CSV route ─────────────────────────────────────────────────────────


def _vuln(cve, severity="High"):
    return WazuhAgentVulnerabilities(cve=cve, severity=severity, name="openssl", version="3.0.2", title=f"{cve} in openssl")


async def _read(response):
    return "".join([chunk if isinstance(chunk, str) else chunk.decode() async for chunk in response.body_iterator])


def test_the_csv_carries_each_known_score_and_leaves_the_others_empty():
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = SimpleNamespace(agent_id="001", customer_code="ACME")
    session.execute = AsyncMock(return_value=result)
    vulnerabilities = WazuhAgentVulnerabilitiesResponse(
        vulnerabilities=[_vuln("CVE-1"), _vuln("CVE-2")],
        success=True,
        message="ok",
    )
    lookup = AsyncMock(return_value={"CVE-1": "0.97"})

    with (
        patch.object(agent_routes.customer_access_handler, "filter_query_by_customer_access", AsyncMock(side_effect=lambda u, s, q, f: q)),
        patch.object(agent_routes, "check_wazuh_manager_version", AsyncMock(return_value=True)),
        patch.object(agent_routes, "collect_agent_vulnerabilities_new", AsyncMock(return_value=vulnerabilities)),
        patch.object(agent_routes, "collect_epss_scores", lookup),
    ):

        async def run():
            response = await agent_routes.get_agent_vulnerabilities_csv(
                agent_id="001",
                vulnerability_severity=VulnSeverity.All,
                current_user=SimpleNamespace(id=7, username="acme.viewer", role_id=4),
                session=session,
            )
            return response, await _read(response)

        response, body = asyncio.run(run())

    assert lookup.await_count == 1  # one lookup for the whole export
    rows = list(csv.DictReader(io.StringIO(body)))
    assert [(r["CVE"], r["EPSS Score"]) for r in rows] == [("CVE-1", "0.97"), ("CVE-2", "")]
    assert response.headers["content-disposition"] == "attachment; filename=001_vulnerabilities.csv"
