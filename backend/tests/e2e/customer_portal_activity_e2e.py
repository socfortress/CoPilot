"""E2E for #1284 (the Customer Portal Activity page) — NOT collected by pytest (needs a live
MySQL); run by hand.

The disposable MySQL on 13306 (see customer_portal_overview_e2e.py's docstring), then:

    .venv/bin/python tests/e2e/customer_portal_activity_e2e.py

Real routers, a real portal login, real SQL. The seed's SLA clocks are replaced by ones at
known times around now, and every expectation below is computed in Python from the rows
themselves, independently of the endpoint's SQL:

  A) the switch: off for a customer without a row, admin-only to flip, audited, and the
     row goes with its customer;
  B) the portal user's 30 days and the 30 before, slice by slice: sources, severities (a
     NULL one is the deployment default), detections, assets, tags; an alert whose
     creation time ingest moved, but which reached the SOC long ago, is not new;
  C) **a click lists exactly what was counted**: every slice of both periods, asked of the
     alerts list with the window the page returned, gives the same total;
  D) the SOC's verdicts (rates over reviewed alerts only) and cases by type and status;
  E) another customer's alerts never count; a customer whose switch is off counts for
     nobody, the SOC included, until it is turned on;
  F) a tag-restricted analyst counts only the alerts their tags let them see, in the page
     and in the list it links to;
  G) bounded and light: 7d / 30d / 90d only, a token required, a handful of statements;
  H) the migration downgrades and upgrades again.

Exits non-zero when a check fails.
"""

import asyncio
import datetime
import os
import sys
from collections import defaultdict

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerPortalActivitySettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import AlertTag  # noqa: E402
from app.incidents.models import AlertToTag  # noqa: E402
from app.incidents.models import Asset  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.services.alert_severity import default_severity  # noqa: E402
from app.incidents.services.alert_severity import normalize_severity  # noqa: E402
from app.soc_management.models.sla import AlertSlaTracking  # noqa: E402
from app.soc_management.models.sla import CaseSlaTracking  # noqa: E402
from app.time_utils import now_utc  # noqa: E402
from app.time_utils import to_naive_utc  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import StatementCounter  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.customer_portal_overview_trend_e2e import TAG_ANALYST  # noqa: E402
from tests.e2e.customer_portal_overview_trend_e2e import add_tag_analyst  # noqa: E402
from tests.e2e.customer_portal_overview_trend_e2e import (  # noqa: E402
    remove_tag_analyst,
)
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PASSWORD  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import TAG_VIP  # noqa: E402
from tests.e2e.portal_overview_seed import alert_name  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []
ACTIVITY = "/customer_portal/activity"
LIST = "/incidents/db_operations/alerts/filter"
TMP_CUSTOMER = "E2E_ACT_TMP"
D = datetime.timedelta(days=1)

# When each of A's alerts reached the SOC, by seed index. 5 is also "last seen" an hour
# ago: ingest moved its creation time, which must not make it new.
A_OPENED = {0: 2 * D, 1: 5 * D, 2: 12 * D, 3: 40 * D, 4: 45 * D, 5: 70 * D}
# (verdict, reason) set on some of A's alerts.
A_VERDICTS = {0: ("TRUE_POSITIVE", None), 1: ("FALSE_POSITIVE", "RULE_TOO_SENSITIVE"), 3: ("FALSE_POSITIVE", "EXPECTED_ACTIVITY")}
# A's cases: (name, opened ago).
A_CASES = {0: ("[INC] E2E activity ransomware", 1 * D), 1: ("Re: [rfi] E2E activity question", 35 * D), 2: ("E2E activity plain", 3 * D)}
B_OPENED = 1 * D


def check(name, passed, detail=""):
    """The detail is printed only for a failure: it is what explains it."""
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


async def place_clocks(now: datetime.datetime) -> dict:
    """Clocks at known times, verdicts and case names; returns A's alert ids by seed index."""
    async with AsyncSession(async_engine) as s:
        ids = {}
        for code in (CUST_A, CUST_B):
            rows = (await s.execute(select(Alert.id, Alert.alert_name).where(Alert.customer_code == code))).all()
            ids[code] = {name: alert_id for alert_id, name in rows}
        a_ids = {i: ids[CUST_A][alert_name(CUST_A, i)] for i in A_OPENED}
        case_ids = {
            code: [row[0] for row in (await s.execute(select(Case.id).where(Case.customer_code == code).order_by(Case.id))).all()]
            for code in (CUST_A, CUST_B)
        }
        everything = [i for by_name in ids.values() for i in by_name.values()]
        await s.execute(delete(AlertSlaTracking).where(AlertSlaTracking.alert_id.in_(everything)))
        await s.execute(delete(CaseSlaTracking).where(CaseSlaTracking.case_id.in_([i for c in case_ids.values() for i in c])))

        def clock(model, key, item_id, ago):
            return model(**{key: item_id}, severity="High", opened_at=now - ago, tracked=True)

        for i, ago in A_OPENED.items():
            s.add(clock(AlertSlaTracking, "alert_id", a_ids[i], ago))
        for alert_id in ids[CUST_B].values():
            s.add(clock(AlertSlaTracking, "alert_id", alert_id, B_OPENED))
        for i, (name, ago) in A_CASES.items():
            s.add(clock(CaseSlaTracking, "case_id", case_ids[CUST_A][i], ago))
            await s.execute(update(Case).where(Case.id == case_ids[CUST_A][i]).values(case_name=name))
        for case_id in case_ids[CUST_B]:
            s.add(clock(CaseSlaTracking, "case_id", case_id, B_OPENED))
        for i, (verdict, reason) in A_VERDICTS.items():
            await s.execute(update(Alert).where(Alert.id == a_ids[i]).values(verdict=verdict, verdict_reason=reason))
        await s.execute(update(Alert).where(Alert.id == a_ids[5]).values(alert_creation_time=now - datetime.timedelta(hours=1)))
        await s.commit()
        return a_ids


async def facts(codes, tags_only=None) -> list:
    """Every alert of ``codes`` with what the page groups by, read straight from the tables."""
    async with AsyncSession(async_engine) as s:
        rows = (
            await s.execute(
                select(
                    Alert.id,
                    Alert.source,
                    Alert.severity,
                    Alert.alert_name,
                    Alert.verdict,
                    Alert.verdict_reason,
                    AlertSlaTracking.opened_at,
                )
                .join(AlertSlaTracking, AlertSlaTracking.alert_id == Alert.id)
                .where(Alert.customer_code.in_(codes)),
            )
        ).all()
        ids = [row[0] for row in rows]
        assets, tags = defaultdict(set), defaultdict(set)
        for alert_id, name in (await s.execute(select(Asset.alert_linked, Asset.asset_name).where(Asset.alert_linked.in_(ids)))).all():
            assets[alert_id].add(name)
        tag_rows = await s.execute(
            select(AlertToTag.alert_id, AlertTag.tag).join(AlertTag, AlertTag.id == AlertToTag.tag_id).where(AlertToTag.alert_id.in_(ids)),
        )
        for alert_id, tag in tag_rows.all():
            tags[alert_id].add(tag)
    out = []
    for alert_id, source, severity, name, verdict, reason, opened in rows:
        if tags_only and not (tags[alert_id] & tags_only):
            continue
        out.append(
            {
                "source": source or "Unknown",
                "severity": normalize_severity(severity) or default_severity(),
                "name": name,
                "verdict": verdict,
                "reason": reason,
                "opened": opened,
                "assets": assets[alert_id],
                "tags": tags[alert_id],
            },
        )
    return out


def period_of(opened: datetime.datetime, body: dict):
    since, until, previous_since = (datetime.datetime.strptime(body[k], "%Y-%m-%dT%H:%M:%SZ") for k in ("since", "until", "previous_since"))
    if since <= opened < until:
        return 0
    if previous_since <= opened < since:
        return 1
    return None


def expected_slices(rows: list, body: dict) -> dict:
    """slice kind -> key -> [current, previous]."""
    out = {kind: defaultdict(lambda: [0, 0]) for kind in ("source", "severity", "name", "asset", "tag")}
    for row in rows:
        index = period_of(row["opened"], body)
        if index is None:
            continue
        out["source"][row["source"]][index] += 1
        out["severity"][row["severity"]][index] += 1
        out["name"][row["name"]][index] += 1
        for asset in row["assets"]:
            out["asset"][asset][index] += 1
        for tag in row["tags"]:
            out["tag"][tag][index] += 1
    return {kind: dict(values) for kind, values in out.items()}


def answered(items: list) -> dict:
    return {item["key"]: [item["count"], item["previous"]] for item in items}


def busy(values: dict) -> dict:
    """What a top list keeps: keys with something in the current period."""
    return {key: pair for key, pair in values.items() if pair[0] > 0}


async def main():
    fixture = await seed(quiet=True)  # noqa: F841 — seeds the users, customers and alerts
    now = to_naive_utc(now_utc()).replace(microsecond=0)
    await place_clocks(now)
    counter = StatementCounter()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
        login = await client.post("/auth/token/customer-portal", data={"username": PORTAL_USER, "password": PASSWORD})
        portal = {"Authorization": f"Bearer {login.json()['access_token']}"}
        admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}

        async def activity(headers=portal, **params):
            response = await client.get(ACTIVITY, params=params, headers=headers)
            return response.status_code, response.json()

        async def listed(headers=portal, **params):
            response = await client.get(LIST, params={"page_size": 100, **params}, headers=headers)
            return response.json().get("total_filtered")

        print("\n=== A) the switch ===")
        status, body = await activity(customer_codes=[CUST_A])
        check(
            "on for A (seeded): the page reads A",
            status == 200 and body["enabled"] and body["customer_codes"] == [CUST_A],
            str(body)[:160],
        )
        status, body = await activity(headers=admin, customer_codes=[CUST_B])
        check("off for B (no row), even for the SOC", status == 200 and body["enabled"] is False, str(body)[:160])
        availability = (await client.get(f"{ACTIVITY}/availability", headers=portal)).json()
        check("the portal user's availability: on", availability["enabled"] is True, str(availability))
        response = await client.put(f"{ACTIVITY}/settings/{CUST_B}", json={"enabled": True}, headers=portal)
        check("a portal user cannot flip it", response.status_code == 403, str(response.status_code))
        response = await client.put(f"{ACTIVITY}/settings/{CUST_B}", json={"enabled": True}, headers=admin)
        check("the admin turns B on", response.status_code == 200 and response.json()["settings"]["enabled"] is True, response.text[:160])
        async with AsyncSession(async_engine) as s:
            audit = (
                (
                    await s.execute(
                        select(AuditLog)
                        .where(AuditLog.action == "activity.settings_update", AuditLog.customer_code == CUST_B)
                        .order_by(AuditLog.id.desc()),
                    )
                )
                .scalars()
                .first()
            )
            check(
                "audited with the old and new value",
                audit is not None and audit.old_value == {"enabled": False} and audit.new_value == {"enabled": True},
                str(audit and (audit.old_value, audit.new_value)),
            )
            if audit:
                await s.execute(delete(AuditLog).where(AuditLog.customer_code.in_([CUST_A, CUST_B, TMP_CUSTOMER])))
            # The row goes with its customer.
            s.add(Customers(customer_code=TMP_CUSTOMER, customer_name="E2E activity tmp"))
            await s.commit()
            s.add(CustomerPortalActivitySettings(customer_code=TMP_CUSTOMER, enabled=True))
            await s.commit()
            await s.execute(delete(Customers).where(Customers.customer_code == TMP_CUSTOMER))
            await s.commit()
            left = (
                await s.execute(select(CustomerPortalActivitySettings).where(CustomerPortalActivitySettings.customer_code == TMP_CUSTOMER))
            ).first()
            check("deleting a customer deletes its switch (ON DELETE CASCADE)", left is None)
        await client.put(f"{ACTIVITY}/settings/{CUST_B}", json={"enabled": False}, headers=admin)

        print("\n=== B) the portal user's 30 days and the 30 before ===")
        status, body = await activity(range="30d")
        check("200", status == 200, str(body)[:160])
        rows_a = await facts([CUST_A])
        want = expected_slices(rows_a, body)
        alerts = body["alerts"]
        check("no section failed", alerts["error"] is None and body["verdicts"]["error"] is None and body["cases"]["error"] is None)
        opened = [sum(1 for row in rows_a if period_of(row["opened"], body) == i) for i in (0, 1)]
        check(
            "opened: 3 this period (2, 5, 12 days ago), 2 before (40, 45)",
            [alerts["opened"]["count"], alerts["opened"]["previous"]] == opened == [3, 2],
            f"{alerts['opened']} vs {opened}",
        )
        check(
            "the alert last seen an hour ago but opened 70 days ago is not new",
            period_of(now - A_OPENED[5], body) is None and alerts["opened"]["count"] == 3,
        )
        check(
            "sources",
            answered(alerts["by_source"]) == busy(want["source"]) or answered(alerts["by_source"]) == want["source"],
            f"{answered(alerts['by_source'])} vs {want['source']}",
        )
        severity = {key: pair for key, pair in answered(alerts["by_severity"]).items() if pair != [0, 0]}
        check("severities, a NULL one counted as the default", severity == want["severity"], f"{severity} vs {want['severity']}")
        check(
            "every severity level listed, most severe first",
            [i["key"] for i in alerts["by_severity"]] == ["Critical", "High", "Medium", "Low", "Informational"],
        )
        check(
            "detections",
            answered(alerts["top_detections"]) == busy(want["name"]),
            f"{answered(alerts['top_detections'])} vs {want['name']}",
        )
        check(
            "assets: an alert per asset",
            answered(alerts["top_assets"]) == busy(want["asset"]),
            f"{answered(alerts['top_assets'])} vs {want['asset']}",
        )
        check("tags", answered(alerts["top_tags"]) == busy(want["tag"]), f"{answered(alerts['top_tags'])} vs {want['tag']}")
        counts = [item["count"] for item in alerts["top_detections"]]
        check("top lists busiest first", counts == sorted(counts, reverse=True), str(counts))

        print("\n=== C) a click lists exactly what was counted ===")
        windows = (
            ("this period", {"opened_from": body["since"], "opened_before": body["until"]}, 0),
            ("the period before", {"opened_from": body["previous_since"], "opened_before": body["since"]}, 1),
        )
        mismatches = []
        compared = 0
        for label, window, index in windows:
            for kind, items, param in (
                ("source", alerts["by_source"], lambda key: {"source": key}),
                ("asset", alerts["top_assets"], lambda key: {"asset_name": key}),
                ("tag", alerts["top_tags"], lambda key: {"tags": [key]}),
                ("detection", alerts["top_detections"], lambda key: {"alert_name": key}),
            ):
                for item in items:
                    shown = item["count"] if index == 0 else item["previous"]
                    total = await listed(**window, **param(item["key"]))
                    compared += 1
                    if total != shown:
                        mismatches.append(f"{label} {kind} {item['key']}: {total} listed, {shown} shown")
            total = await listed(**window)
            compared += 1
            if total != [alerts["opened"]["count"], alerts["opened"]["previous"]][index]:
                mismatches.append(f"{label} all: {total}")
        check(f"every slice of both periods ({compared} lists) matches its count", not mismatches and compared > 10, "; ".join(mismatches))
        check(
            "the detection link is exact, not a search",
            await listed(alert_name=alert_name(CUST_A, 1)) == 1 and await listed(alert_title=alert_name(CUST_A, 1)) == 1,
        )
        status = (await client.get(LIST, params={"opened_from": body["until"], "opened_before": body["since"]}, headers=portal)).status_code
        check("a reversed window is a 422", status == 422, str(status))

        print("\n=== D) verdicts and cases ===")
        verdicts = body["verdicts"]
        current = [row for row in rows_a if period_of(row["opened"], body) == 0]
        reviewed = [row for row in current if row["verdict"]]
        fp = [row for row in reviewed if row["verdict"] == "FALSE_POSITIVE"]
        check(
            "this period: 2 reviewed of 3, one false positive (50%)",
            (verdicts["current"]["reviewed"], verdicts["current"]["false_positive"], verdicts["current"]["false_positive_rate"])
            == (len(reviewed), len(fp), 50.0)
            and verdicts["current"]["coverage_rate"] == 66.7,
            str(verdicts["current"]),
        )
        check(
            "the period before: one reviewed, a false positive (100%)",
            (verdicts["previous"]["reviewed"], verdicts["previous"]["false_positive_rate"]) == (1, 100.0),
            str(verdicts["previous"]),
        )
        check(
            "reasons, with their labels, both periods",
            answered(verdicts["reasons"]) == {"RULE_TOO_SENSITIVE": [1, 0]}
            and verdicts["reasons"][0]["label"] == "Detection rule too sensitive",
            str(verdicts["reasons"]),
        )
        check(
            "the noisiest detection",
            [(n["name"], n["false_positives"], n["reviewed"]) for n in verdicts["noisy_detections"]] == [(alert_name(CUST_A, 1), 1, 1)],
            str(verdicts["noisy_detections"]),
        )
        cases = body["cases"]
        check(
            "cases opened: 2 this period, 1 before",
            [cases["opened"]["count"], cases["opened"]["previous"]] == [2, 1],
            str(cases["opened"]),
        )
        check(
            "cases by type from the name's prefix",
            answered(cases["by_type"]) == {"INC": [1, 0], "RFI": [0, 1], "OTHER": [1, 0]},
            str(cases["by_type"]),
        )
        check("cases by where they stand now", sum(pair[0] for pair in answered(cases["by_status"]).values()) == 2, str(cases["by_status"]))

        print("\n=== E) other customers ===")
        check("B's sources never appear for the portal user", "Beta" not in str(body) and CUST_B not in str(body))
        status, body_b = await activity(customer_codes=[CUST_B])
        check("asking for B by code: off, nothing read", status == 200 and body_b["enabled"] is False)
        status, soc = await activity(headers=admin, range="30d")
        check(
            "the SOC, with B off: A's alone",
            soc["customer_codes"] == [CUST_A] and soc["alerts"]["opened"]["count"] == 3,
            str(soc["customer_codes"]),
        )
        await client.put(f"{ACTIVITY}/settings/{CUST_B}", json={"enabled": True}, headers=admin)
        status, soc = await activity(headers=admin, range="30d")
        b_rows = await facts([CUST_B])
        check(
            "with B on: A's and B's",
            soc["customer_codes"] == [CUST_A, CUST_B] and soc["alerts"]["opened"]["count"] == 3 + len(b_rows),
            f"{soc['customer_codes']} {soc['alerts']['opened']}",
        )
        check("the portal user still reads A's alone", (await activity())[1]["alerts"]["opened"]["count"] == 3)
        await client.put(f"{ACTIVITY}/settings/{CUST_B}", json={"enabled": False}, headers=admin)

        print("\n=== F) a tag-restricted analyst ===")
        settings_id, previous = await add_tag_analyst()
        try:
            analyst = {"Authorization": f"Bearer {await AuthHandler().encode_token(TAG_ANALYST)}"}
            status, tagged = await activity(headers=analyst, range="90d")
            vip_rows = await facts([CUST_A], tags_only={TAG_VIP})
            want_vip = expected_slices(vip_rows, tagged)
            check(
                "only the VIP alerts count",
                status == 200 and answered(tagged["alerts"]["by_source"]) == busy(want_vip["source"]),
                f"{answered(tagged['alerts']['by_source'])} vs {want_vip['source']}",
            )
            vip_now = tagged["alerts"]["opened"]["count"]
            total = await listed(headers=analyst, opened_from=tagged["since"], opened_before=tagged["until"])
            check("and the list it links to shows the same", total == vip_now, f"{total} vs {vip_now}")
        finally:
            await remove_tag_analyst(settings_id, previous)

        print("\n=== G) bounded and light ===")
        check("1y: 422", (await activity(range="1y"))[0] == 422)
        check("without a token: 401", (await client.get(ACTIVITY)).status_code == 401)
        status, body7 = await activity(range="7d")
        check("7 days: the alerts opened 2 and 5 days ago", body7["alerts"]["opened"]["count"] == 2, str(body7["alerts"]["opened"]))
        status, body90 = await activity(range="90d")
        check("90 days: all six", body90["alerts"]["opened"]["count"] == 6, str(body90["alerts"]["opened"]))
        counter.reset()
        await activity(range="30d")
        reads = [s for s in counter.statements if "soc_sla_" in s]
        check("one statement per breakdown: 5 for alerts, 3 for verdicts, 1 for cases", len(reads) == 9, str(len(reads)))
        check("the whole request stays small", len(counter.statements) <= 14, f"{len(counter.statements)} statements")
        grouped = [s for s in reads if "incident_management_alert" in s and "GROUP BY" in s]
        lacking = [s[:200] for s in grouped if s.count("count(distinct(CASE WHEN") < 2]
        check("alerts counted DISTINCT, both periods in one statement", len(grouped) == 8 and not lacking, f"{len(grouped)} {lacking}")

    async with AsyncSession(async_engine) as s:
        await cleanup(s)

    print("\n=== H) the migration round trip ===")
    from alembic import command
    from alembic.config import Config
    from app.db.db_session import SQLALCHEMY_DATABASE_URI

    config = Config("alembic/alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))

    async def table_exists() -> bool:
        async with AsyncSession(async_engine) as s:
            return bool((await s.execute(text("SHOW TABLES LIKE 'customer_portal_activity_settings'"))).first())

    await asyncio.to_thread(command.downgrade, config, "f1278a0b1c2d")
    check("downgrade drops the table", not await table_exists())
    await asyncio.to_thread(command.upgrade, config, "head")
    check("upgrade brings it back", await table_exists())
    await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
