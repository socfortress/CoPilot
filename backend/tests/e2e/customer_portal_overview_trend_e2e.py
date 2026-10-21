"""E2E for #1273 (the Customer Portal Overview's trend) — NOT collected by pytest (needs a
live MySQL); run by hand.

The disposable MySQL on 13306 and the seed of customer_portal_overview_e2e.py (see its
docstring), then:

    .venv/bin/python tests/e2e/customer_portal_overview_trend_e2e.py

Real routers, a real portal login, real SQL. The seed's SLA tracking rows are replaced by
ones at known times around now, so every count below is computed from the same table:

  A) the portal user's 30 days, hour by hour, exactly: opened from `opened_at`, closed from
     `resolved_at`, the current hour included, nothing older than the window;
  B) 7 days drops what happened before them, while an old alert closed this week still
     counts as closed;
  C) another customer's alerts and cases never count, even when asked for by code;
  D) a tag-restricted analyst counts only the alerts their tags let them see (the PDF
     report's aggregation would count them all);
  E) bounded and light: the range is 7d or 30d, and the counts take two queries per entity;
  F) the absolute Net: how many were open when the window starts (opened before it, not
     resolved before it), a closed item without resolved_at never counted open, and that
     anchor plus each hour's opened − closed landing exactly on what is open now.

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
from sqlalchemy import func  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.models.users import UserTagAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import AlertTag  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.models import TagAccessSettings  # noqa: E402
from app.soc_management.models.sla import AlertSlaTracking  # noqa: E402
from app.soc_management.models.sla import CaseSlaTracking  # noqa: E402
from app.time_utils import now_utc  # noqa: E402
from app.time_utils import to_naive_utc  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import StatementCounter  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import ALERT_ROWS_A  # noqa: E402
from tests.e2e.portal_overview_seed import CASES_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PASSWORD  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import TAG_VIP  # noqa: E402
from tests.e2e.portal_overview_seed import alert_name  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []
TREND = "/customer_portal/overview/trend"
TAG_ANALYST = "e2e_ov_trend_tag_analyst"
NOW = to_naive_utc(now_utc()).replace(microsecond=0)
H, D = datetime.timedelta(hours=1), datetime.timedelta(days=1)

# A's alerts, by seed index: (opened ago, closed ago or None). Index 1 and 3 carry the VIP tag.
# Index 5 is CLOSED with no resolved_at (what the SLA backfill left for a closed alert that
# had no time_closed): opened before both windows, it must never count as open.
A_ALERTS = {
    0: (datetime.timedelta(minutes=30), None),  # this very hour
    1: (2 * D, 1 * D),
    2: (3 * D, 3 * D - 2 * H),
    3: (10 * D, 9 * D),  # outside 7 days, inside 30
    4: (40 * D, 5 * D),  # opened before the window, closed inside both
    5: (35 * D, None),
}
A_ALERT_STATUSES = {i: row[0] for i, row in enumerate(ALERT_ROWS_A)}
A_CASE_STATUSES = dict(enumerate(CASES_A))
A_CASES = {0: (1 * D, None), 1: (5 * D, 2 * D), 2: (20 * D, None)}
B_OPENED = 1 * D  # every alert and case of B: opened a day ago, never closed


def check(name, passed, detail=""):
    """The detail is printed only for a failure: it is what explains it."""
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


def hour_of(moment: datetime.datetime) -> str:
    return moment.replace(minute=0, second=0).strftime("%Y-%m-%dT%H:00:00Z")


def expected(alerts: dict, cases: dict, days: int, statuses=None) -> dict:
    """hour -> [alerts_opened, alerts_closed, cases_opened, cases_closed], within the window.

    An item CLOSED without a closing time is left out, as the endpoint leaves it out.
    """
    statuses = statuses or (A_ALERT_STATUSES, A_CASE_STATUSES)
    until = NOW.replace(minute=0, second=0) + H
    since = until - (days + 1) * D
    counts = defaultdict(lambda: [0, 0, 0, 0])
    for rows, offset, status in ((alerts, 0, statuses[0]), (cases, 2, statuses[1])):
        for i, (opened_ago, closed_ago) in rows.items():
            if closed_ago is None and status.get(i) == "CLOSED":
                continue
            for slot, ago in ((offset, opened_ago), (offset + 1, closed_ago)):
                if ago is None:
                    continue
                moment = NOW - ago
                if since <= moment < until:
                    counts[hour_of(moment)][slot] += 1
    return dict(counts)


def open_at(rows: dict, statuses: dict, ago: datetime.timedelta) -> int:
    """How many were open at NOW - ago: opened before, not resolved before; no resolved_at counts only if not CLOSED."""
    count = 0
    for i, (opened_ago, closed_ago) in rows.items():
        if opened_ago <= ago:
            continue
        if (closed_ago is None and statuses[i] != "CLOSED") or (closed_ago is not None and closed_ago <= ago):
            count += 1
    return count


def since_ago(days: int) -> datetime.timedelta:
    return NOW - (NOW.replace(minute=0, second=0) + H - (days + 1) * D)


def answered(body: dict) -> dict:
    return {h["hour"]: [h["alerts_opened"], h["alerts_closed"], h["cases_opened"], h["cases_closed"]] for h in body["hours"]}


async def place_clocks() -> None:
    """Replace the seed's tracking rows with ones at known times."""
    async with AsyncSession(async_engine) as s:
        alert_ids = {}
        for code in (CUST_A, CUST_B):
            rows = (await s.execute(select(Alert.id, Alert.alert_name).where(Alert.customer_code == code))).all()
            alert_ids[code] = {name: alert_id for alert_id, name in rows}
        case_ids = {
            code: [row[0] for row in (await s.execute(select(Case.id).where(Case.customer_code == code).order_by(Case.id))).all()]
            for code in (CUST_A, CUST_B)
        }
        everything = [i for ids in alert_ids.values() for i in ids.values()]
        await s.execute(delete(AlertSlaTracking).where(AlertSlaTracking.alert_id.in_(everything)))
        await s.execute(delete(CaseSlaTracking).where(CaseSlaTracking.case_id.in_([i for ids in case_ids.values() for i in ids])))

        def clock(model, key, item_id, opened_ago, closed_ago):
            return model(
                **{key: item_id},
                severity="High",
                opened_at=NOW - opened_ago,
                resolved_at=None if closed_ago is None else NOW - closed_ago,
                tracked=True,
            )

        for i, (opened_ago, closed_ago) in A_ALERTS.items():
            s.add(clock(AlertSlaTracking, "alert_id", alert_ids[CUST_A][alert_name(CUST_A, i)], opened_ago, closed_ago))
        for i, (opened_ago, closed_ago) in A_CASES.items():
            s.add(clock(CaseSlaTracking, "case_id", case_ids[CUST_A][i], opened_ago, closed_ago))
        for alert_id in alert_ids[CUST_B].values():
            s.add(clock(AlertSlaTracking, "alert_id", alert_id, B_OPENED, None))
        for case_id in case_ids[CUST_B]:
            s.add(clock(CaseSlaTracking, "case_id", case_id, B_OPENED, None))
        await s.commit()
        # B's rows have no closing time: its CLOSED ones are left out of the counts.
        b_alerts = (await s.execute(select(func.count()).where(Alert.customer_code == CUST_B, Alert.status != "CLOSED"))).scalar_one()
        b_cases = (await s.execute(select(func.count()).where(Case.customer_code == CUST_B, Case.case_status != "CLOSED"))).scalar_one()
        return b_alerts, b_cases


async def add_tag_analyst():
    """An analyst of A who may see only VIP-tagged alerts, with tag RBAC switched on."""
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        settings = (await s.execute(select(TagAccessSettings))).scalars().first()
        previous = (settings.enabled, settings.untagged_alert_behavior) if settings else None
        if not settings:
            settings = TagAccessSettings()
            s.add(settings)
        settings.enabled, settings.untagged_alert_behavior = True, "admin_only"
        analyst = User(
            username=TAG_ANALYST,
            password=AuthHandler().get_password_hash(PASSWORD),
            email=f"{TAG_ANALYST}@e2e.example",
            role_id=2,
        )
        s.add(analyst)
        await s.commit()
        vip = (await s.execute(select(AlertTag).where(AlertTag.tag == TAG_VIP))).scalars().one()
        s.add(UserCustomerAccess(user_id=analyst.id, customer_code=CUST_A))
        s.add(UserTagAccess(user_id=analyst.id, tag_id=vip.id))
        await s.commit()
        return settings.id, previous


async def remove_tag_analyst(settings_id, previous):
    async with AsyncSession(async_engine) as s:
        analyst = (await s.execute(select(User).where(User.username == TAG_ANALYST))).scalars().first()
        if analyst:
            await s.execute(delete(UserTagAccess).where(UserTagAccess.user_id == analyst.id))
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == analyst.id))
            await s.delete(analyst)
        settings = await s.get(TagAccessSettings, settings_id)
        if previous is None:
            await s.delete(settings)
        else:
            settings.enabled, settings.untagged_alert_behavior = previous
        await s.commit()


async def main():
    await seed()
    b_alerts, b_cases = await place_clocks()
    counter = StatementCounter()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
        login = await client.post("/auth/token/customer-portal", data={"username": PORTAL_USER, "password": PASSWORD})
        portal = {"Authorization": f"Bearer {login.json()['access_token']}"}
        admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}

        async def trend(headers=portal, **params):
            response = await client.get(TREND, params=params, headers=headers)
            return response.status_code, response.json()

        print("\n=== A) the portal user's 30 days, hour by hour ===")
        status, body = await trend(range="30d")
        check("200", status == 200, str(body)[:160])
        want = expected(A_ALERTS, A_CASES, 30)
        check("every hour exactly: opened from opened_at, closed from resolved_at", answered(body) == want, f"{answered(body)} != {want}")
        check("oldest first", [h["hour"] for h in body["hours"]] == sorted(want), str([h["hour"] for h in body["hours"]]))
        check("the current hour counts", hour_of(NOW - A_ALERTS[0][0]) in answered(body))
        until = (NOW.replace(minute=0, second=0) + H).strftime("%Y-%m-%dT%H:%M:%SZ")
        since = (NOW.replace(minute=0, second=0) + H - 31 * D).strftime("%Y-%m-%dT%H:%M:%SZ")
        check(
            "the window: up to the next whole hour, 30 days and one more",
            (body["since"], body["until"]) == (since, until),
            f"{body['since']} {body['until']}",
        )
        check("an alert opened before the window is not counted opened", hour_of(NOW - A_ALERTS[4][0]) not in answered(body))
        check("no section failed", body["alerts_error"] is None and body["cases_error"] is None)

        print("\n=== B) 7 days ===")
        status, body = await trend(range="7d")
        want7 = expected(A_ALERTS, A_CASES, 7)
        check("every hour exactly", answered(body) == want7, f"{answered(body)} != {want7}")
        totals = [sum(v[i] for v in answered(body).values()) for i in range(4)]
        check(
            "opened 3 alerts and 2 cases this week (the 10-, 20-, 35- and 40-day ones are out)",
            totals[0] == 3 and totals[2] == 2,
            str(totals),
        )
        check(
            "a case CLOSED without a closing time is left out of the 30 days",
            hour_of(NOW - A_CASES[2][0]) not in answered((await trend(range="30d"))[1]),
        )
        check("closed 3 alerts (the 40-day one included) and 1 case", totals[1] == 3 and totals[3] == 1, str(totals))
        check("the default range is 30 days", (await trend())[1]["range"] == "30d")

        print("\n=== C) another customer's never counts ===")
        all_portal = sum(sum(v) for v in answered((await trend(range="30d"))[1]).values())
        check("the portal user's totals are A's alone", all_portal == sum(sum(v) for v in want.values()), str(all_portal))
        status, body = await trend(range="30d", customer_codes=[CUST_B])
        check("asking for B by code: nothing", status == 200 and body["hours"] == [], str(body)[:160])
        status, body = await trend(headers=admin, range="30d", customer_codes=[CUST_B])
        totals = [sum(v[i] for v in answered(body).values()) for i in range(4)]
        check("the SOC asking for B gets B's", totals == [b_alerts, 0, b_cases, 0], str(totals))
        # The SOC without a filter sees every customer: on a shared database other suites' rows
        # count too, so what the rest of it adds is read by asking for those customers by code.
        async with AsyncSession(async_engine) as s:
            others = sorted(
                {
                    code
                    for model in (Alert, Case)
                    for code in (await s.execute(select(model.customer_code).distinct())).scalars()
                    if code and code not in (CUST_A, CUST_B)
                },
            )
        rest = [0, 0, 0, 0]
        if others:
            status, body = await trend(headers=admin, range="30d", customer_codes=others)
            rest = [sum(v[i] for v in answered(body).values()) for i in range(4)]
        status, body = await trend(headers=admin, range="30d")
        totals = [sum(v[i] for v in answered(body).values()) for i in range(4)]
        a = [sum(v[i] for v in want.values()) for i in range(4)]
        both = [a[0] + b_alerts, a[1], a[2] + b_cases, a[3]]
        check(
            "and without a filter, both (and every other customer's)",
            totals == [both[i] + rest[i] for i in range(4)],
            f"{totals} vs {both} + {rest} from {len(others)} other customer(s)",
        )

        print("\n=== D) a tag-restricted analyst ===")
        settings_id, previous = await add_tag_analyst()
        try:
            analyst = {"Authorization": f"Bearer {await AuthHandler().encode_token(TAG_ANALYST)}"}
            status, body = await trend(headers=analyst, range="30d")
            vip = {i: A_ALERTS[i] for i, row in enumerate(ALERT_ROWS_A) if TAG_VIP in row[3]}
            want_vip = {h: c[:2] for h, c in expected(vip, {}, 30).items()}
            got = {h: c[:2] for h, c in answered(body).items() if c[0] or c[1]}
            check("only the alerts their tags let them see", got == want_vip, f"{got} != {want_vip}")
            check("and still every case of their customer", sum(c[2] for c in answered(body).values()) == a[2])
        finally:
            await remove_tag_analyst(settings_id, previous)

        print("\n=== E) bounded and light ===")
        status, body = await trend(range="90d")
        check("a range other than 7d or 30d: 422", status == 422, str(status))
        check("without a token: 401", (await client.get(TREND, params={"range": "7d"})).status_code == 401)
        counter.reset()
        await trend(range="30d")
        reads = [s for s in counter.statements if "soc_sla_" in s]
        check("two queries per entity: the hours and what was open at the start", len(reads) == 4, str(len(reads)))
        check("the hours grouped in SQL", sum("GROUP BY" in s and "UNION ALL" in s for s in reads) == 2)
        check("what was open counted in SQL", sum("count(*)" in s.lower() for s in reads) == 2)
        check("the whole request stays small", len(counter.statements) <= 8, f"{len(counter.statements)} statements")

        print("\n=== F) the absolute Net ===")
        for days, range_ in ((30, "30d"), (7, "7d")):
            body = (await trend(range=range_))[1]
            want_alerts = open_at(A_ALERTS, A_ALERT_STATUSES, since_ago(days))
            want_cases = open_at(A_CASES, A_CASE_STATUSES, since_ago(days))
            check(
                f"{range_}: open at the start, alerts {want_alerts} and cases {want_cases}",
                (body["alerts_open_at_since"], body["cases_open_at_since"]) == (want_alerts, want_cases),
                f"{body['alerts_open_at_since']}, {body['cases_open_at_since']}",
            )
            hours = answered(body)
            end_alerts = body["alerts_open_at_since"] + sum(v[0] - v[1] for v in hours.values())
            end_cases = body["cases_open_at_since"] + sum(v[2] - v[3] for v in hours.values())
            now_alerts = open_at(A_ALERTS, A_ALERT_STATUSES, datetime.timedelta(0))
            now_cases = open_at(A_CASES, A_CASE_STATUSES, datetime.timedelta(0))
            check(
                f"{range_}: the start plus every hour lands on what is open now ({now_alerts} alerts, {now_cases} cases)",
                (end_alerts, end_cases) == (now_alerts, now_cases),
                f"{end_alerts}, {end_cases}",
            )
        check(
            "an alert opened before the window, CLOSED without resolved_at, is not open",
            open_at({5: A_ALERTS[5]}, A_ALERT_STATUSES, since_ago(30)) == 0,
        )
        check(
            "the 30 days start with one open alert: the 40-day one, closed 5 days ago",
            (await trend(range="30d"))[1]["alerts_open_at_since"] == 1,
        )
        body = (await trend(range="30d", customer_codes=[CUST_B]))[1]
        check(
            "another customer's: nothing open, not unknown",
            (body["alerts_open_at_since"], body["cases_open_at_since"]) == (0, 0),
            str(body)[:120],
        )
        body = (await trend(headers=admin, range="30d", customer_codes=[CUST_B]))[1]
        check(
            "the SOC asking for B: B's open at the start (none, all opened a day ago)",
            (body["alerts_open_at_since"], body["cases_open_at_since"]) == (0, 0),
        )
        hours = answered(body)
        check(
            "and at the end, B's open ones: the start plus its hours",
            (sum(v[0] - v[1] for v in hours.values()), sum(v[2] - v[3] for v in hours.values())) == (b_alerts, b_cases),
        )

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
