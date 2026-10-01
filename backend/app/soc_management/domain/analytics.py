"""From facts to metrics: every number on the SOC Management dashboard is computed here.

The services load two kinds of facts per entity and hand them over unchanged:

- **window facts** — items opened *or* resolved in the period (and its previous period,
  for the deltas);
- **open facts**   — items open right now, whenever they were opened (the backlog).

Two semantics, chosen per question and stated in each docstring:

- **Cohort** (by ``opened_at``): "how did we do on what arrived in September?" — volumes,
  response/resolution times, SLA compliance, per-rule and per-customer figures.
- **Activity** (by when the action happened): "what did each analyst do in September?"
  — acknowledgements and resolutions attributed to whoever performed them.

**Only tracked items carry timings.** Items that existed before tracking began were
backfilled with an approximate ``opened_at`` and no response history; they still count
in volumes and workload, but never in a duration or a compliance figure, where an
invented clock would be worse than none.
"""

from __future__ import annotations

from collections import Counter
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Set
from typing import Tuple

from app.soc_management.domain.lifecycle import CLOSED
from app.soc_management.domain.periods import Bucket
from app.soc_management.domain.periods import Period
from app.soc_management.domain.periods import bucket_starts
from app.soc_management.domain.periods import floor_to
from app.soc_management.domain.policy import SEVERITIES_DESC
from app.soc_management.domain.policy import SlaEntity
from app.soc_management.domain.sla import Compliance
from app.soc_management.domain.sla import SlaState
from app.soc_management.domain.sla import evaluate
from app.soc_management.domain.sla import summarize
from app.soc_management.domain.stats import DurationStats
from app.soc_management.domain.stats import describe

TRUE_POSITIVE = "TRUE_POSITIVE"
FALSE_POSITIVE = "FALSE_POSITIVE"

#: A rule is "noisy" once enough of its alerts were reviewed to judge it, and most
#: reviews called it a false positive. Five keeps one unlucky week from branding a rule.
NOISY_MIN_REVIEWED = 5
NOISY_FP_RATE = 50.0


# ── facts ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ItemFact:
    """One alert or case with its SLA tracking, as the dashboard needs it."""

    entity: SlaEntity
    id: int
    title: str
    customer_code: Optional[str]
    severity: str
    status: str
    assigned_to: Optional[str]
    opened_at: datetime
    tracked: bool
    ack_due_at: Optional[datetime] = None
    resolve_due_at: Optional[datetime] = None
    first_ack_at: Optional[datetime] = None
    first_ack_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    reopen_count: int = 0
    # Alert-only facts; neutral defaults for cases.
    source: Optional[str] = None
    verdict: Optional[str] = None
    in_case: bool = False
    escalated: bool = False

    @property
    def is_open(self) -> bool:
        return self.status != CLOSED

    @property
    def tta(self) -> Optional[float]:
        if not self.tracked or self.first_ack_at is None:
            return None
        return (self.first_ack_at - self.opened_at).total_seconds()

    @property
    def ttr(self) -> Optional[float]:
        if not self.tracked or self.resolved_at is None:
            return None
        return (self.resolved_at - self.opened_at).total_seconds()

    @property
    def ack_achieved_at(self) -> Optional[datetime]:
        """When the response clock stopped: the first SOC response, else the resolution.

        An item a customer closed before anyone at the SOC touched it needs no response
        any more; its clock stops there instead of running into a breach forever.
        """
        return self.first_ack_at or self.resolved_at

    def ack_state(self, now: datetime) -> SlaState:
        if not self.tracked:
            return SlaState.NOT_TRACKED
        return evaluate(self.opened_at, self.ack_due_at, self.ack_achieved_at, now)

    def resolve_state(self, now: datetime) -> SlaState:
        if not self.tracked:
            return SlaState.NOT_TRACKED
        return evaluate(self.opened_at, self.resolve_due_at, self.resolved_at, now)

    def live_state(self, now: datetime) -> SlaState:
        """The state of the clocks still running — what needs action on an open item.

        A clock already achieved, even late, needs nothing more: a late acknowledgement
        stays a breach in the compliance figures, but it is not what a manager chases.
        """
        running = []
        if self.ack_achieved_at is None:
            running.append(self.ack_state(now))
        if self.resolved_at is None:
            running.append(self.resolve_state(now))
        for state in (SlaState.BREACHED, SlaState.AT_RISK, SlaState.ON_TRACK):
            if state in running:
                return state
        return SlaState.NOT_TRACKED


# ── results ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SlaPair:
    ack: Compliance = field(default_factory=Compliance)
    resolve: Compliance = field(default_factory=Compliance)


@dataclass(frozen=True)
class EntityHeadline:
    opened: int = 0
    resolved: int = 0
    resolved_by_customer: int = 0
    tta: DurationStats = field(default_factory=DurationStats)
    ttr: DurationStats = field(default_factory=DurationStats)
    sla: SlaPair = field(default_factory=SlaPair)
    reopened: int = 0


@dataclass(frozen=True)
class Headline:
    alerts: EntityHeadline
    cases: EntityHeadline
    #: Of alerts opened in the period that were reviewed, the share judged false positives.
    false_positive_rate: Optional[float]
    reviewed_alerts: int
    #: Share of alerts opened in the period that ended up in a case.
    case_conversion_rate: Optional[float]
    escalated_alerts: int


@dataclass(frozen=True)
class SeverityRow:
    entity: SlaEntity
    severity: str
    opened: int
    resolved: int
    open_now: int
    breached_now: int
    tta: DurationStats
    ttr: DurationStats
    sla: SlaPair


@dataclass(frozen=True)
class TrendPoint:
    start: datetime
    alerts_opened: int = 0
    alerts_resolved: int = 0
    cases_opened: int = 0
    cases_resolved: int = 0
    #: Resolve-clock compliance of alerts + cases opened in this bucket.
    sla_rate: Optional[float] = None
    alert_ttr_median: Optional[float] = None


@dataclass(frozen=True)
class AnalystRow:
    username: str
    alerts_acknowledged: int = 0
    alerts_resolved: int = 0
    cases_acknowledged: int = 0
    cases_resolved: int = 0
    tta: DurationStats = field(default_factory=DurationStats)
    ttr: DurationStats = field(default_factory=DurationStats)
    #: Resolve-clock compliance of the items this analyst resolved in the period.
    sla: Compliance = field(default_factory=Compliance)
    open_alerts: int = 0
    open_cases: int = 0
    at_risk: int = 0
    breached: int = 0


@dataclass(frozen=True)
class RuleRow:
    alert_name: str
    sources: List[str]
    alerts: int
    in_case: int
    reviewed: int
    true_positives: int
    false_positives: int
    false_positive_rate: Optional[float]
    noisy: bool
    open_now: int
    ttr: DurationStats
    sla: Compliance
    #: Alerts opened per trend bucket — the sparkline.
    series: List[int]


@dataclass(frozen=True)
class CustomerRow:
    customer_code: str
    alerts: int
    cases: int
    resolved: int
    open_now: int
    breached_now: int
    alert_ttr: DurationStats
    case_ttr: DurationStats
    alert_sla: Compliance
    case_sla: Compliance
    top_rule: Optional[str]


@dataclass(frozen=True)
class SeverityLoad:
    severity: str
    alerts: int = 0
    cases: int = 0
    breached: int = 0
    at_risk: int = 0


@dataclass(frozen=True)
class AssigneeLoad:
    username: str
    alerts: int = 0
    cases: int = 0
    breached: int = 0
    at_risk: int = 0


@dataclass(frozen=True)
class Workload:
    open_alerts: int
    open_cases: int
    unassigned_alerts: int
    unassigned_cases: int
    #: Opening time of the oldest unassigned open item — the queue's tail.
    oldest_unassigned_at: Optional[datetime]
    breached: int
    at_risk: int
    by_severity: List[SeverityLoad]
    by_assignee: List[AssigneeLoad]


@dataclass(frozen=True)
class AttentionItem:
    entity: SlaEntity
    id: int
    title: str
    customer_code: Optional[str]
    severity: str
    status: str
    assigned_to: Optional[str]
    opened_at: datetime
    state: SlaState
    #: Which clock drives the state: "ack" or "resolve".
    clock: str
    due_at: Optional[datetime]
    #: Positive when late; negative = seconds still left (at-risk items).
    overdue_seconds: float


# ── helpers ──────────────────────────────────────────────────────────────────


def _rate(numerator: int, denominator: int) -> Optional[float]:
    return round(numerator * 100.0 / denominator, 1) if denominator else None


def _opened_in(facts: Iterable[ItemFact], period: Period) -> List[ItemFact]:
    return [f for f in facts if period.contains(f.opened_at)]


def _resolved_in(facts: Iterable[ItemFact], period: Period) -> List[ItemFact]:
    return [f for f in facts if f.resolved_at is not None and period.contains(f.resolved_at)]


def _sla_pair(facts: Sequence[ItemFact], now: datetime) -> SlaPair:
    return SlaPair(ack=summarize(f.ack_state(now) for f in facts), resolve=summarize(f.resolve_state(now) for f in facts))


def _is_breached(fact: ItemFact, now: datetime) -> bool:
    """Open and overdue on a clock that is still running."""
    return fact.is_open and fact.live_state(now) is SlaState.BREACHED


def _is_at_risk(fact: ItemFact, now: datetime) -> bool:
    return fact.is_open and fact.live_state(now) is SlaState.AT_RISK


# ── sections ─────────────────────────────────────────────────────────────────


def entity_headline(facts: Sequence[ItemFact], period: Period, now: datetime, soc_usernames: Set[str]) -> EntityHeadline:
    """Cohort figures for one entity, plus resolutions *performed* in the period."""
    cohort = _opened_in(facts, period)
    resolved = _resolved_in(facts, period)
    return EntityHeadline(
        opened=len(cohort),
        resolved=len(resolved),
        resolved_by_customer=sum(1 for f in resolved if f.resolved_by and f.resolved_by not in soc_usernames),
        tta=describe(f.tta for f in cohort),
        ttr=describe(f.ttr for f in cohort),
        sla=_sla_pair(cohort, now),
        reopened=sum(1 for f in cohort if f.reopen_count > 0),
    )


def headline(
    alerts: Sequence[ItemFact],
    cases: Sequence[ItemFact],
    period: Period,
    now: datetime,
    soc_usernames: Set[str],
) -> Headline:
    cohort = _opened_in(alerts, period)
    reviewed = [f for f in cohort if f.verdict in (TRUE_POSITIVE, FALSE_POSITIVE)]
    false_positives = sum(1 for f in reviewed if f.verdict == FALSE_POSITIVE)
    return Headline(
        alerts=entity_headline(alerts, period, now, soc_usernames),
        cases=entity_headline(cases, period, now, soc_usernames),
        false_positive_rate=_rate(false_positives, len(reviewed)),
        reviewed_alerts=len(reviewed),
        case_conversion_rate=_rate(sum(1 for f in cohort if f.in_case), len(cohort)),
        escalated_alerts=sum(1 for f in cohort if f.escalated),
    )


def severity_rows(
    entity: SlaEntity,
    window: Sequence[ItemFact],
    open_now: Sequence[ItemFact],
    period: Period,
    now: datetime,
) -> List[SeverityRow]:
    cohort = _opened_in(window, period)
    resolved = _resolved_in(window, period)
    rows = []
    for severity in SEVERITIES_DESC:
        of_cohort = [f for f in cohort if f.severity == severity]
        of_open = [f for f in open_now if f.severity == severity]
        rows.append(
            SeverityRow(
                entity=entity,
                severity=severity,
                opened=len(of_cohort),
                resolved=sum(1 for f in resolved if f.severity == severity),
                open_now=len(of_open),
                breached_now=sum(1 for f in of_open if _is_breached(f, now)),
                tta=describe(f.tta for f in of_cohort),
                ttr=describe(f.ttr for f in of_cohort),
                sla=_sla_pair(of_cohort, now),
            ),
        )
    return rows


def trends(alerts: Sequence[ItemFact], cases: Sequence[ItemFact], period: Period, bucket: Bucket, now: datetime) -> List[TrendPoint]:
    starts = bucket_starts(period, bucket)
    index = {start: i for i, start in enumerate(starts)}

    def slot(moment: Optional[datetime]) -> Optional[int]:
        if moment is None or not period.contains(moment):
            return None
        return index.get(floor_to(moment, bucket))

    alerts_opened = [0] * len(starts)
    alerts_resolved = [0] * len(starts)
    cases_opened = [0] * len(starts)
    cases_resolved = [0] * len(starts)
    resolve_states: List[List[SlaState]] = [[] for _ in starts]
    alert_ttrs: List[List[float]] = [[] for _ in starts]

    for facts, opened, resolved in ((alerts, alerts_opened, alerts_resolved), (cases, cases_opened, cases_resolved)):
        for fact in facts:
            opened_slot = slot(fact.opened_at)
            if opened_slot is not None:
                opened[opened_slot] += 1
                resolve_states[opened_slot].append(fact.resolve_state(now))
                if fact.entity is SlaEntity.ALERT and fact.ttr is not None:
                    alert_ttrs[opened_slot].append(fact.ttr)
            resolved_slot = slot(fact.resolved_at)
            if resolved_slot is not None:
                resolved[resolved_slot] += 1

    return [
        TrendPoint(
            start=start,
            alerts_opened=alerts_opened[i],
            alerts_resolved=alerts_resolved[i],
            cases_opened=cases_opened[i],
            cases_resolved=cases_resolved[i],
            sla_rate=summarize(resolve_states[i]).rate,
            alert_ttr_median=describe(alert_ttrs[i]).median,
        )
        for i, start in enumerate(starts)
    ]


def analysts(
    alerts: Sequence[ItemFact],
    cases: Sequence[ItemFact],
    open_alerts: Sequence[ItemFact],
    open_cases: Sequence[ItemFact],
    period: Period,
    now: datetime,
    soc_usernames: Set[str],
) -> List[AnalystRow]:
    """Activity in the period, attributed to whoever performed it, plus their open load.

    Only SOC users appear: a portal user who closed their own alert resolved it, but is
    not a member of the team this table measures.
    """
    acked: Dict[str, List[ItemFact]] = defaultdict(list)
    resolved: Dict[str, List[ItemFact]] = defaultdict(list)
    for fact in (*alerts, *cases):
        if fact.first_ack_by in soc_usernames and fact.first_ack_at is not None and period.contains(fact.first_ack_at):
            acked[fact.first_ack_by].append(fact)
        if fact.resolved_by in soc_usernames and fact.resolved_at is not None and period.contains(fact.resolved_at):
            resolved[fact.resolved_by].append(fact)

    load: Dict[str, List[ItemFact]] = defaultdict(list)
    for fact in (*open_alerts, *open_cases):
        if fact.assigned_to in soc_usernames:
            load[fact.assigned_to].append(fact)

    rows = []
    for username in sorted(set(acked) | set(resolved) | set(load)):
        mine_acked, mine_resolved, mine_open = acked[username], resolved[username], load[username]
        rows.append(
            AnalystRow(
                username=username,
                alerts_acknowledged=sum(1 for f in mine_acked if f.entity is SlaEntity.ALERT),
                alerts_resolved=sum(1 for f in mine_resolved if f.entity is SlaEntity.ALERT),
                cases_acknowledged=sum(1 for f in mine_acked if f.entity is SlaEntity.CASE),
                cases_resolved=sum(1 for f in mine_resolved if f.entity is SlaEntity.CASE),
                tta=describe(f.tta for f in mine_acked),
                ttr=describe(f.ttr for f in mine_resolved),
                sla=summarize(f.resolve_state(now) for f in mine_resolved),
                open_alerts=sum(1 for f in mine_open if f.entity is SlaEntity.ALERT),
                open_cases=sum(1 for f in mine_open if f.entity is SlaEntity.CASE),
                at_risk=sum(1 for f in mine_open if _is_at_risk(f, now)),
                breached=sum(1 for f in mine_open if _is_breached(f, now)),
            ),
        )
    rows.sort(key=lambda r: (-(r.alerts_resolved + r.cases_resolved), -(r.open_alerts + r.open_cases), r.username))
    return rows


def rules(
    alerts: Sequence[ItemFact],
    period: Period,
    bucket: Bucket,
    now: datetime,
    limit: int = 25,
) -> List[RuleRow]:
    """Detection rules (alert titles) by volume, with how their alerts were judged.

    The grouping key is the alert title: it is what every source maps its rule name to
    at ingest (``incident_management_alerttitlefieldname``), so it is the one identity
    shared by Wazuh, Graylog, WAF and the rest.
    """
    cohort = _opened_in(alerts, period)
    by_name: Dict[str, List[ItemFact]] = defaultdict(list)
    for fact in cohort:
        by_name[fact.title].append(fact)

    starts = bucket_starts(period, bucket)
    index = {start: i for i, start in enumerate(starts)}

    ranked = sorted(by_name.items(), key=lambda item: (-len(item[1]), item[0]))[:limit]
    rows = []
    for name, facts in ranked:
        reviewed = [f for f in facts if f.verdict in (TRUE_POSITIVE, FALSE_POSITIVE)]
        false_positives = sum(1 for f in reviewed if f.verdict == FALSE_POSITIVE)
        fp_rate = _rate(false_positives, len(reviewed))
        series = [0] * len(starts)
        for fact in facts:
            position = index.get(floor_to(fact.opened_at, bucket))
            if position is not None:
                series[position] += 1
        rows.append(
            RuleRow(
                alert_name=name,
                sources=sorted({f.source for f in facts if f.source}),
                alerts=len(facts),
                in_case=sum(1 for f in facts if f.in_case),
                reviewed=len(reviewed),
                true_positives=len(reviewed) - false_positives,
                false_positives=false_positives,
                false_positive_rate=fp_rate,
                noisy=len(reviewed) >= NOISY_MIN_REVIEWED and fp_rate is not None and fp_rate >= NOISY_FP_RATE,
                open_now=sum(1 for f in facts if f.is_open),
                ttr=describe(f.ttr for f in facts),
                sla=summarize(f.resolve_state(now) for f in facts),
                series=series,
            ),
        )
    return rows


def customers(
    alerts: Sequence[ItemFact],
    cases: Sequence[ItemFact],
    open_alerts: Sequence[ItemFact],
    open_cases: Sequence[ItemFact],
    period: Period,
    now: datetime,
) -> List[CustomerRow]:
    alert_cohort = _opened_in(alerts, period)
    case_cohort = _opened_in(cases, period)
    resolved = _resolved_in((*alerts, *cases), period)

    def group(facts: Iterable[ItemFact]) -> Dict[str, List[ItemFact]]:
        grouped: Dict[str, List[ItemFact]] = defaultdict(list)
        for fact in facts:
            if fact.customer_code:
                grouped[fact.customer_code].append(fact)
        return grouped

    alerts_by, cases_by, resolved_by, open_by = (
        group(alert_cohort),
        group(case_cohort),
        group(resolved),
        group((*open_alerts, *open_cases)),
    )
    rows = []
    for code in sorted(set(alerts_by) | set(cases_by) | set(resolved_by) | set(open_by)):
        its_alerts, its_cases, its_open = alerts_by[code], cases_by[code], open_by[code]
        top = Counter(f.title for f in its_alerts).most_common(1)
        rows.append(
            CustomerRow(
                customer_code=code,
                alerts=len(its_alerts),
                cases=len(its_cases),
                resolved=len(resolved_by[code]),
                open_now=len(its_open),
                breached_now=sum(1 for f in its_open if _is_breached(f, now)),
                alert_ttr=describe(f.ttr for f in its_alerts),
                case_ttr=describe(f.ttr for f in its_cases),
                alert_sla=summarize(f.resolve_state(now) for f in its_alerts),
                case_sla=summarize(f.resolve_state(now) for f in its_cases),
                top_rule=top[0][0] if top else None,
            ),
        )
    rows.sort(key=lambda r: (-(r.alerts + r.cases), r.customer_code))
    return rows


def workload(open_alerts: Sequence[ItemFact], open_cases: Sequence[ItemFact], now: datetime) -> Workload:
    everything = (*open_alerts, *open_cases)
    unassigned = [f for f in everything if not f.assigned_to]

    by_severity = []
    for severity in SEVERITIES_DESC:
        of_severity = [f for f in everything if f.severity == severity]
        by_severity.append(
            SeverityLoad(
                severity=severity,
                alerts=sum(1 for f in of_severity if f.entity is SlaEntity.ALERT),
                cases=sum(1 for f in of_severity if f.entity is SlaEntity.CASE),
                breached=sum(1 for f in of_severity if _is_breached(f, now)),
                at_risk=sum(1 for f in of_severity if _is_at_risk(f, now)),
            ),
        )

    by_user: Dict[str, List[ItemFact]] = defaultdict(list)
    for fact in everything:
        if fact.assigned_to:
            by_user[fact.assigned_to].append(fact)
    by_assignee = [
        AssigneeLoad(
            username=username,
            alerts=sum(1 for f in facts if f.entity is SlaEntity.ALERT),
            cases=sum(1 for f in facts if f.entity is SlaEntity.CASE),
            breached=sum(1 for f in facts if _is_breached(f, now)),
            at_risk=sum(1 for f in facts if _is_at_risk(f, now)),
        )
        for username, facts in by_user.items()
    ]
    by_assignee.sort(key=lambda load: (-(load.alerts + load.cases), load.username))

    return Workload(
        open_alerts=len(open_alerts),
        open_cases=len(open_cases),
        unassigned_alerts=sum(1 for f in open_alerts if not f.assigned_to),
        unassigned_cases=sum(1 for f in open_cases if not f.assigned_to),
        oldest_unassigned_at=min((f.opened_at for f in unassigned), default=None),
        breached=sum(1 for f in everything if _is_breached(f, now)),
        at_risk=sum(1 for f in everything if _is_at_risk(f, now)),
        by_severity=by_severity,
        by_assignee=by_assignee,
    )


def attention_items(facts: Iterable[ItemFact], now: datetime, limit: int = 50) -> List[AttentionItem]:
    """Open items that need a manager's eye: breached first (most overdue on top), then
    at-risk (closest to breaching on top). Only running clocks count — see ``live_state``."""
    items: List[AttentionItem] = []
    for fact in facts:
        if not fact.is_open:
            continue
        chosen = _most_urgent(fact, now)
        if chosen is None:
            continue
        clock, state, due_at = chosen
        items.append(
            AttentionItem(
                entity=fact.entity,
                id=fact.id,
                title=fact.title,
                customer_code=fact.customer_code,
                severity=fact.severity,
                status=fact.status,
                assigned_to=fact.assigned_to,
                opened_at=fact.opened_at,
                state=state,
                clock=clock,
                due_at=due_at,
                overdue_seconds=(now - due_at).total_seconds(),
            ),
        )

    def severity_rank(severity: str) -> int:
        return SEVERITIES_DESC.index(severity) if severity in SEVERITIES_DESC else len(SEVERITIES_DESC)

    items.sort(key=lambda i: (i.state is not SlaState.BREACHED, -i.overdue_seconds, severity_rank(i.severity), i.id))
    return items[:limit]


def _most_urgent(fact: ItemFact, now: datetime) -> Optional[Tuple[str, SlaState, datetime]]:
    """The running clock to act on: the most overdue breached one, else the at-risk one
    closest to its due time."""
    running: List[Tuple[str, SlaState, datetime]] = []
    if fact.ack_achieved_at is None and fact.ack_due_at is not None:
        running.append(("ack", fact.ack_state(now), fact.ack_due_at))
    if fact.resolved_at is None and fact.resolve_due_at is not None:
        running.append(("resolve", fact.resolve_state(now), fact.resolve_due_at))
    breached = [clock for clock in running if clock[1] is SlaState.BREACHED]
    if breached:
        return min(breached, key=lambda clock: clock[2])
    at_risk = [clock for clock in running if clock[1] is SlaState.AT_RISK]
    if at_risk:
        return min(at_risk, key=lambda clock: clock[2])
    return None
