"""E2E for #1289 against a real indexer — NOT collected by pytest; run by hand.

The Exposure page aggregates in the Wazuh indexer (OpenSearch). ``tests/exposure_support``
evaluates its query DSL for the other tests; this one runs the very same queries on a real
OpenSearch, through the page's own client code, and checks two things:

  A) OpenSearch accepts every query the page builds (the terms ordering by a metric, the
     bucket_sort, the agent pair script, the case-insensitive wildcard, the date minimums,
     the scroll of the export);
  B) it answers exactly what the stand-in answers, for the same documents, scopes and
     filters, so the stand-in the other tests trust is faithful.

A disposable OpenSearch, security off, on 127.0.0.1:19200:

    docker run -d --name copilot-e2e-opensearch -p 127.0.0.1:19200:9200 \\
      -e discovery.type=single-node -e DISABLE_SECURITY_PLUGIN=true \\
      -e DISABLE_INSTALL_DEMO_CONFIG=true -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" \\
      opensearchproject/opensearch:2.13.0

    .venv/bin/python tests/e2e/customer_portal_exposure_indexer_e2e.py

No MySQL. Without an OpenSearch at E2E_OPENSEARCH_URL it says so and exits 0.
"""

import asyncio
import csv
import io
import os
import sys
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

from elasticsearch7 import AsyncElasticsearch  # noqa: E402

from app.customer_portal.services import exposure_vulnerabilities as vulns  # noqa: E402
from app.customer_portal.services.exposure import ExposureScope  # noqa: E402
from app.customer_portal.services.exposure import ScopedAgent  # noqa: E402
from tests.exposure_support import FakeIndexer  # noqa: E402
from tests.exposure_support import vuln  # noqa: E402

URL = os.environ.get("E2E_OPENSEARCH_URL", "http://127.0.0.1:19200")
INDEX = "wazuh-states-vulnerabilities-e2e-exposure"

# The fields the page reads, typed as Wazuh's vulnerability-states template types them.
MAPPINGS = {
    "properties": {
        "agent": {"properties": {"id": {"type": "keyword"}, "name": {"type": "keyword"}}},
        "package": {"properties": {"name": {"type": "keyword"}, "version": {"type": "keyword"}}},
        "vulnerability": {
            "properties": {
                "id": {"type": "keyword"},
                "severity": {"type": "keyword"},
                "score": {"properties": {"base": {"type": "float"}}},
                "detected_at": {"type": "date"},
                "published_at": {"type": "date"},
                "description": {"type": "keyword", "ignore_above": 1024},
                "reference": {"type": "keyword", "ignore_above": 1024},
            },
        },
    },
}

AGENTS = [ScopedAgent("001", "web-01", "ACME"), ScopedAgent("002", "db-01", "ACME"), ScopedAgent("010", "app-01", "INITECH")]
SCOPES = {
    "ACME": ExposureScope(customer_codes=["ACME"], agents=AGENTS[:2]),
    "ACME+INITECH": ExposureScope(customer_codes=["ACME", "INITECH"], agents=AGENTS),
}
DOCS = [
    vuln("001", "web-01", "CVE-2026-0001", "Critical", 9.8, package="openssl", detected="2026-09-02T10:00:00Z"),
    vuln("001", "web-01", "CVE-2026-0001", "Critical", 9.8, package="libssl", detected="2026-08-20T10:00:00Z"),
    vuln("002", "db-01", "CVE-2026-0001", "Critical", 9.8, package="openssl", detected="2026-09-05T10:00:00Z"),
    vuln("002", "db-01", "CVE-2026-0002", "High", 7.5, package="OpenJDK", version="17"),
    vuln("001", "web-01", "CVE-2026-0003", "Low", 3.1, package="curl"),
    vuln("002", "db-01", "CVE-2026-0004", "Medium", None, package="bash"),
    vuln("010", "app-01", "CVE-2026-0002", "High", 7.5, package="OpenJDK"),
    vuln("010", "app-01", "CVE-2026-0005", "High", 8.1, package="nginx"),
    # Another manager's agents: one shares 001 with web-01, one shares db-01's name.
    vuln("001", "db-01", "CVE-2099-0001", "Critical", 10.0, package="ghost"),
    vuln("077", "web-01", "CVE-2099-0002", "Critical", 10.0, package="ghost"),
    # A severity the page does not count.
    vuln("001", "web-01", "CVE-2026-0009", "Untriaged", 1.0, package="zlib"),
]
QUERIES = [
    {"severity": None, "search": None, "page": 1, "page_size": 25},
    {"severity": "High", "search": None, "page": 1, "page_size": 25},
    {"severity": None, "search": "ssl", "page": 1, "page_size": 25},
    {"severity": None, "search": "OPENjdk", "page": 1, "page_size": 25},
    {"severity": None, "search": "cve-2026-000", "page": 2, "page_size": 2},
    {"severity": "Critical", "search": "*", "page": 1, "page_size": 25},
]

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


async def reachable() -> bool:
    client = AsyncElasticsearch([URL])
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.close()


async def load():
    client = AsyncElasticsearch([URL])
    try:
        await client.indices.delete(index=INDEX, ignore=[404])
        await client.indices.create(index=INDEX, body={"settings": {"number_of_shards": 1, "number_of_replicas": 0}, "mappings": MAPPINGS})
        for i, doc in enumerate(DOCS):
            await client.index(index=INDEX, id=str(i), body=doc)
        await client.indices.refresh(index=INDEX)
    finally:
        await client.close()


async def drop():
    client = AsyncElasticsearch([URL])
    try:
        await client.indices.delete(index=INDEX, ignore=[404])
    finally:
        await client.close()


async def run_page(scope, query):
    response = await vulns.vulnerabilities(scope, **query)
    return response.model_dump()


async def main():
    if not await reachable():
        print(f"SKIPPED: no OpenSearch at {URL} (see the docstring to start one)")
        return True
    await load()
    fake = FakeIndexer(DOCS)
    epss = AsyncMock(side_effect=lambda cves: {})

    async def real_client(_name="Wazuh-Indexer"):
        return AsyncElasticsearch([URL])

    try:
        for label, scope in SCOPES.items():
            print(f"\n=== {label} ===")
            for query in QUERIES:
                with patch.object(vulns, "create_wazuh_indexer_client_async", real_client), patch.object(vulns, "epss_scores", epss):
                    real = await run_page(scope, query)
                with patch.object(vulns, "indexer_search", fake.search), patch.object(vulns, "epss_scores", epss):
                    stand_in = await run_page(scope, query)
                check(f"{query}: OpenSearch accepts the queries", real["error"] is None, str(real.get("error")))
                check(
                    f"{query}: and answers what the stand-in answers",
                    real == stand_in,
                    f"real {real['severities']} {real['totals']} {[r['cve_id'] for r in real['cves']]} vs "
                    f"{stand_in['severities']} {stand_in['totals']} {[r['cve_id'] for r in stand_in['cves']]}",
                )
            check("nothing of another manager's agents", "CVE-2099" not in str(real) and "CVE-2026-0009" not in str(real))

            for cve in ("CVE-2026-0001", "CVE-2026-0002", "CVE-2099-0001"):
                with patch.object(vulns, "create_wazuh_indexer_client_async", real_client), patch.object(vulns, "epss_scores", epss):
                    real = (await vulns.cve_detail(scope, cve)).model_dump()
                with patch.object(vulns, "indexer_search", fake.search), patch.object(vulns, "epss_scores", epss):
                    stand_in = (await vulns.cve_detail(scope, cve)).model_dump()
                check(f"{cve}: the same agents and details", real == stand_in and real["error"] is None, f"{real} vs {stand_in}")

            with patch.object(vulns, "create_wazuh_indexer_client_async", real_client), patch.object(
                vulns,
                "epss_scores",
                epss,
            ), patch.object(
                vulns,
                "EXPORT_BATCH",
                2,
            ):
                real_csv, real_cut = await vulns.export_csv(scope, None, None)
            with patch.object(vulns, "indexer_scroll", fake.scroll), patch.object(vulns, "epss_scores", epss):
                fake_csv, fake_cut = await vulns.export_csv(scope, None, None)
            rows = list(csv.reader(io.StringIO(real_csv)))
            check("the export scrolls every batch and matches", real_csv == fake_csv and not real_cut and not fake_cut, f"{len(rows)} rows")
    finally:
        await drop()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
