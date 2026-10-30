"""Threat Intel for the portal's browser e2e (#1318, customer-portal/cypress/e2e/ioc-enrichment.cy.ts).

Run by Cypress after `portal_overview_seed.py seed`, with the disposable MySQL on 13306:

    python tests/e2e/portal_threat_intel_seed.py connect http://127.0.0.1:2527
    python tests/e2e/portal_threat_intel_seed.py disconnect

``connect`` points the VirusTotal and OpenCTI connector rows at the fake Threat Intel that
cypress.config.ts runs on localhost (the rows are created, marked as this script's, when the
database has none) and puts three IOCs on an open alert of customer A: a public address the fake
knows, a private one, and a domain it does not know. It prints their ids as JSON. ``disconnect``
removes the IOCs, the customers' enrichment rows and the connector rows it created.

The e2e backend runs without its lifespan, so it never syncs connectors itself, and misses are
not cached: the rows written here are what it reads.
"""

import asyncio
import json
import os
import sys

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")

from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.connectors.models import Connectors  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerPortalIocEnrichment  # noqa: E402
from app.db.universal_models import CustomerPortalIocEnrichmentSettings  # noqa: E402
from app.db.universal_models import CustomerPortalIocLookup  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import AlertToIoC  # noqa: E402
from app.incidents.models import IoC  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402

MARKER = "e2e_cy_ti_ioc"
CONNECTOR_MARKER = "e2e_cy_ti_connector"
PUBLIC_IP = "45.155.205.233"
PRIVATE_IP = "10.20.30.40"
UNKNOWN_DOMAIN = "nothing-known.example.org"


async def connect(base_url: str) -> dict:
    async with AsyncSession(async_engine) as s:
        for name in ("VirusTotal", "OpenCTI"):
            url = f"{base_url}/api/v3" if name == "VirusTotal" else base_url
            row = (await s.execute(select(Connectors).where(Connectors.connector_name == name))).scalars().first()
            if row is None:
                row = Connectors(connector_name=name, connector_type="3", connector_url=url, connector_description=CONNECTOR_MARKER)
                s.add(row)
            row.connector_url, row.connector_api_key, row.connector_verified, row.connector_configured = url, "e2e-key", True, True
        alert = (
            (await s.execute(select(Alert).where(Alert.customer_code == CUST_A, Alert.status == "OPEN").order_by(Alert.id).limit(1)))
            .scalars()
            .first()
        )
        if alert is None:
            raise SystemExit("No open alert of customer A: run portal_overview_seed.py seed first")
        alert_id, ids = alert.id, {}  # read before the commit expires the row
        for key, value, kind in (("public", PUBLIC_IP, "IP"), ("private", PRIVATE_IP, "IP"), ("unknown", UNKNOWN_DOMAIN, "DOMAIN")):
            ioc = IoC(value=value, type=kind, description=MARKER)
            s.add(ioc)
            await s.flush()
            s.add(AlertToIoC(alert_id=alert_id, ioc_id=ioc.id))
            ids[key] = ioc.id
        await s.commit()
        return {"alert_id": alert_id, "iocs": ids, "values": {"public": PUBLIC_IP, "private": PRIVATE_IP, "unknown": UNKNOWN_DOMAIN}}


async def disconnect() -> None:
    async with AsyncSession(async_engine) as s:
        ioc_ids = (await s.execute(select(IoC.id).where(IoC.description == MARKER))).scalars().all()
        if ioc_ids:
            await s.execute(delete(AlertToIoC).where(AlertToIoC.ioc_id.in_(ioc_ids)))
            await s.execute(delete(IoC).where(IoC.id.in_(ioc_ids)))
        for model in (CustomerPortalIocEnrichment, CustomerPortalIocLookup, CustomerPortalIocEnrichmentSettings):
            await s.execute(delete(model).where(model.customer_code.in_([CUST_A, CUST_B])))
        await s.execute(delete(Connectors).where(Connectors.connector_description == CONNECTOR_MARKER))
        await s.commit()


async def _main(command: str, argument: str) -> None:
    if not os.environ["MYSQL_URL"].endswith(":13306") and os.environ.get("E2E_ALLOW_ANY_DB") != "1":
        raise SystemExit(f"Refusing to touch {os.environ['MYSQL_URL']}: not the e2e MySQL on :13306.")
    if command == "connect":
        print(json.dumps(await connect(argument)))
    elif command == "disconnect":
        await disconnect()
    else:
        raise SystemExit(f"unknown command {command!r}: use 'connect <url>' or 'disconnect'")
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2] if len(sys.argv) > 2 else ""))
