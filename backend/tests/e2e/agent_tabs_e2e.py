"""E2E for #1256 (an agent's Vulnerabilities, SCA and Cases in the Customer Portal) — NOT
collected by pytest (needs a live MySQL); run by hand.

Same disposable MySQL on 13306 and the same seed as customer_portal_overview_e2e.py
(see its docstring for the setup), then:

    .venv/bin/python tests/e2e/agent_tabs_e2e.py

Real routers, real MySQL, a real portal login. Wazuh is replaced by a recorder (no Wazuh
here), and so is EPSS:

  A) the portal user reads their own agent's vulnerabilities, SCA policies, a policy's
     checks and both CSV exports;
  B) another customer's agent is a 404 on every one of them, and Wazuh is never asked
     about it;
  C) the agent's cases are its own customer's only: B's case, whose alert names the very
     same host, does not show under A's agent (it did before #1256), each case once;
  D) an admin gets the agent's customer's cases too, not every tenant's on that name.

Exits non-zero when a check fails.
"""

import asyncio
import csv
import io
import os
import sys
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.agents.routes.agents as agent_routes  # noqa: E402
from app.agents.wazuh.schema.agents import WazuhAgentScaPolicyResults  # noqa: E402
from app.agents.wazuh.schema.agents import (  # noqa: E402
    WazuhAgentScaPolicyResultsResponse,
)
from app.agents.wazuh.schema.agents import WazuhAgentScaResponse  # noqa: E402
from app.agents.wazuh.schema.agents import WazuhAgentScaResults  # noqa: E402
from app.agents.wazuh.schema.agents import WazuhAgentVulnerabilities  # noqa: E402
from app.agents.wazuh.schema.agents import (  # noqa: E402
    WazuhAgentVulnerabilitiesResponse,
)
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import PASSWORD  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


class FakeWazuh:
    """What CoPilot asks Wazuh, and fixed answers: no Wazuh in this setup."""

    def __init__(self):
        self.asked: list[tuple[str, str]] = []

    async def vulnerabilities(self, agent_id, vulnerability_severity):
        self.asked.append(("vulnerabilities", agent_id))
        rows = [
            WazuhAgentVulnerabilities(cve="CVE-2026-0001", severity="Critical", name="openssl", version="3.0.2"),
            WazuhAgentVulnerabilities(cve="CVE-2026-0002", severity="High", name="curl", version="7.81.0"),
        ]
        if vulnerability_severity != "All":
            rows = [r for r in rows if r.severity == vulnerability_severity]
        return WazuhAgentVulnerabilitiesResponse(vulnerabilities=rows, success=True, message="faked")

    async def sca(self, agent_id, policy_id=None):
        self.asked.append(("sca", agent_id))
        policy = WazuhAgentScaResults(policy_id="cis_ubuntu22-04", name="CIS Ubuntu 22.04", score=61, total_checks=200)
        return WazuhAgentScaResponse(sca=[policy], success=True, message="faked")

    async def sca_checks(self, agent_id, policy_id, check_id=None):
        self.asked.append(("sca_checks", agent_id))
        checks = [
            WazuhAgentScaPolicyResults(
                id=28500,
                title="Ensure /tmp is a separate partition",
                rationale="r",
                condition="all",
                result="failed",
                policy_id=policy_id,
                remediation="Mount /tmp separately",
                compliance=[],
                rules=[],
            ),
        ]
        return WazuhAgentScaPolicyResultsResponse(sca_policy_results=checks, success=True, message="faked")


async def main():
    ids = await seed()
    mine, theirs = ids["agent_a0"], ids["agent_b0_id"]
    wazuh = FakeWazuh()

    patches = [
        patch.object(agent_routes, "check_wazuh_manager_version", AsyncMock(return_value=True)),
        patch.object(agent_routes, "collect_agent_vulnerabilities_new", wazuh.vulnerabilities),
        patch.object(agent_routes, "collect_agent_sca", wazuh.sca),
        patch.object(agent_routes, "collect_agent_sca_policy_results", wazuh.sca_checks),
        patch.object(agent_routes, "collect_epss_scores", AsyncMock(return_value={"CVE-2026-0001": "0.97"})),
    ]
    for p in patches:
        p.start()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
            login = await client.post("/auth/token/customer-portal", data={"username": PORTAL_USER, "password": PASSWORD})
            portal = {"Authorization": f"Bearer {login.json()['access_token']}"}
            admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}

            def paths(agent_id):
                return {
                    "vulnerabilities": f"/agents/{agent_id}/vulnerabilities/All",
                    "vulnerabilities by severity": f"/agents/{agent_id}/vulnerabilities/Critical",
                    "vulnerabilities CSV": f"/agents/{agent_id}/csv/vulnerabilities/All",
                    "SCA policies": f"/agents/{agent_id}/sca",
                    "a policy's checks": f"/agents/{agent_id}/sca/cis_ubuntu22-04",
                    "SCA CSV": f"/agents/{agent_id}/csv/sca/cis_ubuntu22-04",
                }

            print("\n=== A) the portal user reads their own agent ===")
            got = {name: await client.get(path, headers=portal) for name, path in paths(mine["agent_id"]).items()}
            for name, response in got.items():
                check(f"{name}: 200", response.status_code == 200, f"{response.status_code} {response.text[:120]}")
            check(
                "vulnerabilities: both, and the severity filter narrows them",
                [v["cve"] for v in got["vulnerabilities"].json()["vulnerabilities"]] == ["CVE-2026-0001", "CVE-2026-0002"]
                and [v["cve"] for v in got["vulnerabilities by severity"].json()["vulnerabilities"]] == ["CVE-2026-0001"],
            )
            rows = list(csv.DictReader(io.StringIO(got["vulnerabilities CSV"].text)))
            check(
                "vulnerabilities CSV: one row each, EPSS where known",
                [(r["CVE"], r["EPSS Score"]) for r in rows] == [("CVE-2026-0001", "0.97"), ("CVE-2026-0002", "")],
                str(rows)[:200],
            )
            check("SCA: the policy and its score", got["SCA policies"].json()["sca"][0]["score"] == 61)
            check("SCA: the passed count keeps Wazuh's name", "pass" in got["SCA policies"].json()["sca"][0])
            check("a policy's checks", got["a policy's checks"].json()["sca_policy_results"][0]["result"] == "failed")
            check("SCA CSV: a header and the check", "Ensure /tmp is a separate partition" in got["SCA CSV"].text)

            print("\n=== B) another customer's agent: a 404 everywhere, Wazuh never asked ===")
            wazuh.asked.clear()
            for name, path in paths(theirs).items():
                response = await client.get(path, headers=portal)
                check(f"{name}: 404", response.status_code == 404, f"{response.status_code}")
            check("Wazuh was never asked about it", wazuh.asked == [], str(wazuh.asked))

            print("\n=== C) the agent's cases: its own customer's only ===")
            response = await client.get(f"/agents/{mine['hostname']}/cases", headers=portal)
            case_ids = [c["id"] for c in response.json().get("cases", [])]
            check("200", response.status_code == 200, response.text[:120])
            check("A's case, once", case_ids == [mine["case_id"]], str(case_ids))
            check("never B's case on the same host name", ids["foreign_case_id"] not in case_ids, str(case_ids))
            check(
                "every case is the agent's customer's",
                all(c["customer_code"] == "E2E_OV_A" for c in response.json()["cases"]),
            )
            check("an unknown host: 404", (await client.get("/agents/no-such-host/cases", headers=portal)).status_code == 404)
            check(
                "another customer's agent host: 404",
                (await client.get("/agents/ov-E2E_OV_B-0/cases", headers=portal)).status_code == 404,
            )

            print("\n=== D) an admin: the agent's customer's cases, not every tenant's ===")
            response = await client.get(f"/agents/{mine['hostname']}/cases", headers=admin)
            case_ids = [c["id"] for c in response.json().get("cases", [])]
            check("admin: A's case only", case_ids == [mine["case_id"]], str(case_ids))
    finally:
        for p in patches:
            p.stop()

    async with AsyncSession(async_engine) as s:
        await cleanup(s)
    await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
