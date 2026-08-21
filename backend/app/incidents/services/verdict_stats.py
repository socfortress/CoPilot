"""Aggregations over the alert triage verdict — false-positive reporting (issue #1085).

Every helper takes ``customer_codes`` (a list, or None for "no tenant constraint") rather
than the single ``customer_code`` used by ``customer_report_aggregations``. That is
deliberate: the same questions are asked at two scopes. The per-customer PDF report passes
``[code]``, while the SOC's own monthly review asks "which tenants generate the most false
positives", which is a cross-tenant grouping. Keeping one implementation means the number
in the customer's PDF and the number on the SOC dashboard cannot disagree.

The tri-state verdict is what makes these numbers honest. ``NULL`` is "not yet triaged",
so the false-positive *rate* is computed against reviewed alerts only -- dividing by every
alert ingested would silently improve the rate every time the SOC fell behind on triage,
which is precisely backwards.

Monthly bucketing is done in Python rather than with ``func.year``/``func.month`` so the
same code works on MySQL (production) and SQLite (tests), matching the convention in
``customer_report_aggregations``.
"""
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from sqlalchemy import and_
from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.incidents.models import Alert
from app.incidents.schema.db_operations import AlertVerdict
from app.incidents.schema.db_operations import FalsePositiveReason

FALSE_POSITIVE = AlertVerdict.FALSE_POSITIVE.value
TRUE_POSITIVE = AlertVerdict.TRUE_POSITIVE.value

# Report-facing labels. The stored values are stable identifiers meant for grouping; a
# customer-facing PDF should not print SCREAMING_SNAKE_CASE at an executive reader.
_REASON_LABELS = {
    FalsePositiveReason.EXPECTED_ACTIVITY.value: "Expected / legitimate activity",
    FalsePositiveReason.KNOWN_APPLICATION.value: "Known application or service",
    FalsePositiveReason.AUTHORIZED_USER.value: "Authorized user activity",
    FalsePositiveReason.RULE_TOO_SENSITIVE.value: "Detection rule too sensitive",
    FalsePositiveReason.OTHER.value: "Other",
}


def false_positive_reason_label(reason: Optional[str]) -> str:
    """Human label for a stored reason, falling back to the raw value.

    The fallback matters during a rolling deploy: a reason added to the enum before this
    map is updated still renders something rather than an empty bar label.
    """
    if not reason:
        return "Unspecified"
    return _REASON_LABELS.get(reason, reason)


def _window(customer_codes: Optional[List[str]], date_from: datetime, date_to: datetime):
    """Predicate: alerts created in [date_from, date_to], optionally tenant-scoped.

    ``customer_codes=None`` means no tenant constraint. Callers reached from an HTTP route
    must resolve the caller's accessible customers first and never pass None on their
    behalf -- an empty resolution means "nothing you may see" and must short-circuit,
    because a falsy list here drops the constraint rather than matching no rows.
    """
    predicates = [
        Alert.alert_creation_time >= date_from,
        Alert.alert_creation_time <= date_to,
    ]
    if customer_codes:
        predicates.append(Alert.customer_code.in_(customer_codes))
    return and_(*predicates)


async def verdict_counts(
    session: AsyncSession,
    customer_codes: Optional[List[str]],
    date_from: datetime,
    date_to: datetime,
) -> Dict[str, float]:
    """Headline numbers: how many alerts, how many judged, and the false-positive rate.

    ``false_positive_rate`` is a percentage of *reviewed* alerts (true + false positive),
    not of all alerts. ``coverage_rate`` says how much of the period was actually triaged,
    which is the context that stops the first number being read out of proportion -- a 90%
    false-positive rate over 10 reviewed alerts out of 4000 is a different story from the
    same rate over 4000.
    """
    result = await session.execute(
        select(Alert.verdict, func.count().label("cnt")).where(_window(customer_codes, date_from, date_to)).group_by(Alert.verdict),
    )
    counts = {row[0]: int(row[1]) for row in result.all()}

    false_positive = counts.get(FALSE_POSITIVE, 0)
    true_positive = counts.get(TRUE_POSITIVE, 0)
    untriaged = counts.get(None, 0)
    reviewed = false_positive + true_positive
    total = reviewed + untriaged

    return {
        "total": total,
        "reviewed": reviewed,
        "untriaged": untriaged,
        "true_positive": true_positive,
        "false_positive": false_positive,
        # Guarded: a period where nothing was triaged has no rate, and reporting 0.0 would
        # read as "no false positives" rather than "no data".
        "false_positive_rate": round(false_positive / reviewed * 100, 1) if reviewed else None,
        "coverage_rate": round(reviewed / total * 100, 1) if total else None,
    }


async def false_positives_by_reason(
    session: AsyncSession,
    customer_codes: Optional[List[str]],
    date_from: datetime,
    date_to: datetime,
) -> List[Tuple[str, int]]:
    """Most common false-positive categories, highest first."""
    result = await session.execute(
        select(Alert.verdict_reason, func.count().label("cnt"))
        .where(_window(customer_codes, date_from, date_to), Alert.verdict == FALSE_POSITIVE)
        .group_by(Alert.verdict_reason)
        .order_by(func.count().desc()),
    )
    return [(row[0] or "UNSPECIFIED", int(row[1])) for row in result.all()]


async def top_false_positives_by_alert_name(
    session: AsyncSession,
    customer_codes: Optional[List[str]],
    date_from: datetime,
    date_to: datetime,
    limit: int = 15,
) -> List[Tuple[str, int, int, Optional[float]]]:
    """The detections generating the most false positives -- the detection-tuning list.

    Grouped by ``alert_name``, which is the closest thing to a rule identity CoPilot
    stores: there is no ``rule_id`` column, and the source rule id only exists inside the
    ``incident_management_alertcontext`` JSON blob, which MySQL cannot group by cheaply.
    For Wazuh-sourced alerts the title is effectively per-rule; for other sources it is
    per-alert-type, which is still the right granularity for tuning.

    Each row is ``(alert_name, false_positives, reviewed, false_positive_rate)``. The rate
    matters as much as the count: a detection with 40 false positives out of 400 reviewed
    is noisy, while one with 12 out of 12 is simply wrong, and ordering by raw count alone
    would bury the second behind the first.
    """
    result = await session.execute(
        select(
            Alert.alert_name,
            func.sum(case((Alert.verdict == FALSE_POSITIVE, 1), else_=0)).label("fp"),
            func.sum(case((Alert.verdict.is_not(None), 1), else_=0)).label("reviewed"),
        )
        .where(_window(customer_codes, date_from, date_to))
        .group_by(Alert.alert_name)
        .having(func.sum(case((Alert.verdict == FALSE_POSITIVE, 1), else_=0)) > 0)
        .order_by(func.sum(case((Alert.verdict == FALSE_POSITIVE, 1), else_=0)).desc())
        .limit(limit),
    )
    rows = []
    for name, fp, reviewed in result.all():
        fp = int(fp or 0)
        reviewed = int(reviewed or 0)
        rows.append((name or "Unknown", fp, reviewed, round(fp / reviewed * 100, 1) if reviewed else None))
    return rows


async def false_positives_by_customer(
    session: AsyncSession,
    customer_codes: Optional[List[str]],
    date_from: datetime,
    date_to: datetime,
) -> List[Tuple[str, int, int, Optional[float]]]:
    """False positives per tenant: ``(customer_code, false_positives, reviewed, rate)``.

    Ordered by rate rather than count so a small noisy tenant is not hidden behind a large
    quiet one. Tenants with nothing reviewed are excluded -- they have no rate, and showing
    them as 0% would misreport "not looked at" as "clean".
    """
    result = await session.execute(
        select(
            Alert.customer_code,
            func.sum(case((Alert.verdict == FALSE_POSITIVE, 1), else_=0)).label("fp"),
            func.sum(case((Alert.verdict.is_not(None), 1), else_=0)).label("reviewed"),
        )
        .where(_window(customer_codes, date_from, date_to))
        .group_by(Alert.customer_code)
        .having(func.sum(case((Alert.verdict.is_not(None), 1), else_=0)) > 0),
    )
    rows = []
    for code, fp, reviewed in result.all():
        fp = int(fp or 0)
        reviewed = int(reviewed or 0)
        rows.append((code or "Unknown", fp, reviewed, round(fp / reviewed * 100, 1) if reviewed else None))
    rows.sort(key=lambda r: (r[3] or 0, r[1]), reverse=True)
    return rows


async def false_positive_trend(
    session: AsyncSession,
    customer_codes: Optional[List[str]],
    date_from: datetime,
    date_to: datetime,
) -> List[dict]:
    """Per-month false-positive evolution, bucketed in Python.

    Returns ``{"month": "YYYY-MM", "false_positive": n, "true_positive": n,
    "untriaged": n, "false_positive_rate": pct or None}`` in chronological order. Months
    with no reviewed alerts carry a null rate rather than 0.0, so a gap in triage renders
    as a gap rather than as a month with no false positives.
    """
    rows = await session.execute(
        select(Alert.alert_creation_time, Alert.verdict).where(_window(customer_codes, date_from, date_to)),
    )

    buckets: dict = {}
    for created_at, verdict in rows.all():
        if created_at is None:
            continue
        key = f"{created_at.year:04d}-{created_at.month:02d}"
        bucket = buckets.setdefault(key, {"false_positive": 0, "true_positive": 0, "untriaged": 0})
        if verdict == FALSE_POSITIVE:
            bucket["false_positive"] += 1
        elif verdict == TRUE_POSITIVE:
            bucket["true_positive"] += 1
        else:
            bucket["untriaged"] += 1

    trend = []
    for month in sorted(buckets.keys()):
        bucket = buckets[month]
        reviewed = bucket["false_positive"] + bucket["true_positive"]
        trend.append(
            {
                "month": month,
                "false_positive": bucket["false_positive"],
                "true_positive": bucket["true_positive"],
                "untriaged": bucket["untriaged"],
                "false_positive_rate": round(bucket["false_positive"] / reviewed * 100, 1) if reviewed else None,
            },
        )
    return trend
