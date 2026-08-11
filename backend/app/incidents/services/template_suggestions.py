"""
Smart case-template suggestions (issue #935).

Ranks the case templates already visible to an analyst against the context of
the alert they are about to open a case for, so the common path is "accept the
top suggestion" instead of "browse the whole library".

**This module deliberately introduces no schema.** No table, no column, no
Alembic migration. Every signal it scores on is derived from data that already
exists:

===================  ==========================================================
Signal               Where it comes from
===================  ==========================================================
customer scope       ``CaseTemplate.customer_code`` vs the alert's
source scope         ``CaseTemplate.source`` vs ``Alert.source``
auto-apply condition ``CaseTemplate.match_field`` / ``match_value`` evaluated
                     against the alert's originating document — the exact same
                     check ``pick_templates_for_alert`` performs
alert tags           ``incident_management_alert_to_tag`` → ``…_alerttag.tag``
MITRE technique ids  ``incident_management_alertcontext.context`` (the ingest
                     dictionary already stores ``rule_mitre_id`` and friends),
                     falling back to the raw Wazuh document
Wazuh rule groups    same context blob (``rule_groups``)
alert title keywords ``Alert.alert_name``
usage history        ``CaseTask.template_task_id`` → ``CaseTemplateTask`` →
                     ``CaseTask.case_id`` → ``Case.customer_code``
===================  ==========================================================

The template side of every text comparison is a *corpus* built from the
template's own name, description and task text (title + description +
guidelines). That is what makes this work on day one: existing templates carry
no tags or MITRE columns an operator would have to backfill, but a template
called "Ransomware — host containment" whose tasks mention T1486 already says
everything the scorer needs. Adding explicit metadata columns later would be a
strictly better signal; it is not a precondition for the feature.

Scoring is intentionally additive and explainable. Every point a template earns
comes with a ``SuggestionReason`` naming the signal and the evidence, because a
ranked list an analyst cannot audit is a ranked list an analyst will not trust.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

from loguru import logger
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import AlertTag
from app.incidents.models import AlertToTag
from app.incidents.models import Asset
from app.incidents.models import Case
from app.incidents.models import CaseTask
from app.incidents.models import CaseTemplate
from app.incidents.models import CaseTemplateTask
from app.incidents.schema.case_templates import CaseTemplateSuggestion
from app.incidents.schema.case_templates import CaseTemplateSuggestionListResponse
from app.incidents.schema.case_templates import SuggestionReason
from app.incidents.services.case_templates import _template_to_response

# ---------------------------------------------------------------------------
# Weights
#
# Tunable in one place on purpose. The absolute numbers matter less than their
# ratios; what they encode is:
#
#   - A satisfied auto-apply condition outranks everything, because it is not a
#     heuristic — it is the operator's own explicit rule firing.
#   - Explicit scope (this customer / this source) outranks inferred topical
#     overlap, because scope was configured deliberately and text overlap was
#     not.
#   - Topical signals are capped so a template that happens to name six MITRE
#     techniques cannot bulldoze a correctly-scoped one.
# ---------------------------------------------------------------------------

WEIGHT_CONDITION_MATCH = 40
WEIGHT_CUSTOMER_MATCH = 25
WEIGHT_SOURCE_MATCH = 20

WEIGHT_TAG_MATCH = 10
CAP_TAG_MATCH = 30

WEIGHT_MITRE_MATCH = 15
#: A template naming the parent technique (T1059) when the alert carries a
#: sub-technique (T1059.001) is related but less precise. Partial credit.
WEIGHT_MITRE_PARENT_MATCH = 7
CAP_MITRE_MATCH = 30

WEIGHT_RULE_GROUP_MATCH = 6
CAP_RULE_GROUP_MATCH = 18

WEIGHT_KEYWORD_MATCH = 4
CAP_KEYWORD_MATCH = 12

#: Usage history is a tiebreaker, not a driver — otherwise the template applied
#: most often becomes self-reinforcing and nothing new ever surfaces. Log-scaled
#: so the 40th application counts for far less than the 2nd.
WEIGHT_USAGE_HISTORY_MAX = 12

WEIGHT_IS_DEFAULT = 5

#: Confidence buckets, reported alongside the raw score so the UI can style the
#: top suggestion differently without hard-coding thresholds of its own.
CONFIDENCE_HIGH_THRESHOLD = 55
CONFIDENCE_MEDIUM_THRESHOLD = 25

DEFAULT_SUGGESTION_LIMIT = 5

# ---------------------------------------------------------------------------
# Text handling
# ---------------------------------------------------------------------------

#: ``T1059`` / ``T1059.001``. Wazuh emits the bare technique id; templates tend
#: to mention it inline in a task description ("…see T1486…").
_MITRE_ID_PATTERN = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.IGNORECASE)

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

#: Dropped from alert-title keyword extraction. Deliberately short: this is not
#: a search engine, and an over-eager stoplist silently deletes signal. These
#: are the words that appear in so many alert titles that matching on them tells
#: us nothing about which playbook applies.
_KEYWORD_STOPWORDS: Set[str] = {
    "a",
    "alert",
    "an",
    "and",
    "at",
    "by",
    "detected",
    "detection",
    "event",
    "for",
    "from",
    "has",
    "in",
    "is",
    "of",
    "on",
    "or",
    "possible",
    "potential",
    "rule",
    "suspicious",
    "the",
    "to",
    "was",
    "with",
}

#: Wazuh tags every alert with a handful of structural groups that carry no
#: topical meaning. Matching a template on "syslog" would fire on everything.
_GENERIC_RULE_GROUPS: Set[str] = {
    "attack",
    "attacks",
    "gdpr",
    "gpg13",
    "hipaa",
    "ids",
    "nist_800_53",
    "pci_dss",
    "sca",
    "syscheck",
    "syslog",
    "tsc",
    "wazuh",
}

#: Context keys inspected for Wazuh rule groups. The ingest dictionary is
#: operator-configured, so which of these is actually present varies.
_RULE_GROUP_KEYS = ("rule_groups", "rule_group", "rule.groups")

#: Context keys inspected for MITRE display names (tactic / technique). The ids
#: themselves are picked up by regex over every value, so these only add the
#: human-readable side ("Command and Scripting Interpreter").
_MITRE_NAME_KEYS = (
    "rule_mitre_technique",
    "rule_mitre_tactic",
    "rule.mitre.technique",
    "rule.mitre.tactic",
)

#: Minimum length for a token to be worth matching on. Two-character tokens
#: ("ad", "ps") produce far more false positives than signal inside free text.
_MIN_TOKEN_LENGTH = 3


def _tokenize(text: str) -> List[str]:
    return _TOKEN_PATTERN.findall(text.lower())


def _as_string_list(value: Any) -> List[str]:
    """Flatten a context value into a list of strings.

    Ingest writes these blobs straight through from the source document, so the
    same logical field arrives as a list on one deployment and a delimited
    string on another. Handle both rather than guessing.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [part for part in re.split(r"[,;|]", value) if part.strip()]
    if isinstance(value, (list, tuple, set)):
        out: List[str] = []
        for item in value:
            out.extend(_as_string_list(item))
        return out
    return [str(value)]


def _flatten_values(value: Any, out: List[str]) -> None:
    """Collect every scalar inside a nested context value as a string."""
    if value is None:
        return
    if isinstance(value, dict):
        for nested in value.values():
            _flatten_values(nested, out)
    elif isinstance(value, (list, tuple, set)):
        for nested in value:
            _flatten_values(nested, out)
    else:
        out.append(str(value))


def _normalize_mitre_id(value: str) -> str:
    return value.strip().upper()


def _extract_mitre_ids(text: str) -> Set[str]:
    return {_normalize_mitre_id(m) for m in _MITRE_ID_PATTERN.findall(text)}


def _mitre_parent(technique_id: str) -> Optional[str]:
    """``T1059.001`` → ``T1059``. Returns None for an already-parent id."""
    if "." in technique_id:
        return technique_id.split(".", 1)[0]
    return None


def _contains_phrase(corpus_tokens: Set[str], corpus_text: str, phrase: str) -> bool:
    """Does ``corpus_text`` contain ``phrase`` as whole word(s)?

    Alert tags and rule groups use every separator convention there is
    (``lateral-movement``, ``lateral_movement``, ``LateralMovement``), so the
    phrase is compared token-wise: a single token is a set membership test, a
    multi-token phrase falls back to a whitespace-tolerant regex over the
    normalized corpus so word order still has to match.
    """
    tokens = _tokenize(phrase)
    tokens = [t for t in tokens if len(t) >= _MIN_TOKEN_LENGTH]
    if not tokens:
        return False
    if len(tokens) == 1:
        return tokens[0] in corpus_tokens
    return re.search(r"\b" + r"\W+".join(re.escape(t) for t in tokens) + r"\b", corpus_text) is not None


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------


@dataclass
class AlertSignals:
    """Everything the scorer knows about the case-to-be.

    Populated from an alert when one is supplied, or from bare
    ``customer_code`` / ``source`` when the analyst is creating a case manually
    and there is no alert to read. Both paths score through the same function;
    the manual one simply has empty topical signals and therefore leans on
    scope, usage history and ``is_default``.

    Severity is deliberately absent. Templates carry no severity dimension, so
    the only way to score on it would be text-matching "critical" / "high"
    against the template's prose — which fires on any playbook that happens to
    use the word, and says nothing about whether it fits. Giving severity real
    weight needs a real column on the template first.
    """

    customer_code: Optional[str] = None
    source: Optional[str] = None
    alert_id: Optional[int] = None
    alert_name: Optional[str] = None
    tags: List[str] = dataclass_field(default_factory=list)
    mitre_ids: Set[str] = dataclass_field(default_factory=set)
    mitre_names: List[str] = dataclass_field(default_factory=list)
    rule_groups: List[str] = dataclass_field(default_factory=list)
    keywords: List[str] = dataclass_field(default_factory=list)
    #: Merged key/value bag used to evaluate ``match_field`` / ``match_value``.
    #: Empty dict means "we could not read the document", which is scored
    #: differently from "we read it and the condition was false".
    document: Dict[str, Any] = dataclass_field(default_factory=dict)
    document_available: bool = False


async def _load_alert_tags(alert_id: int, session: AsyncSession) -> List[str]:
    stmt = select(AlertTag.tag).join(AlertToTag, AlertToTag.tag_id == AlertTag.id).where(AlertToTag.alert_id == alert_id)
    return [row for row in (await session.execute(stmt)).scalars().all() if row]


async def _load_alert_context(alert_id: int, session: AsyncSession) -> Dict[str, Any]:
    """Merge the stored context blobs of every asset on this alert.

    ``incident_management_alertcontext`` is written at ingest from the
    operator-configured field dictionary, so it is a local read — no OpenSearch
    round-trip — and it is where ``rule_mitre_id`` already lives. An alert with
    several assets normally has identical context on each; where they differ the
    lowest asset id wins, matching ``_fetch_raw_event_for_alert``'s tie-break.
    """
    stmt = (
        select(AlertContext.context)
        .join(Asset, Asset.alert_context_id == AlertContext.id)
        .where(Asset.alert_linked == alert_id)
        .order_by(Asset.id.asc())
    )
    merged: Dict[str, Any] = {}
    for context in (await session.execute(stmt)).scalars().all():
        if not isinstance(context, dict):
            continue
        for key, value in context.items():
            merged.setdefault(key, value)
    return merged


def _signals_from_document(signals: AlertSignals, document: Dict[str, Any]) -> None:
    """Fold MITRE ids/names and rule groups out of a context/raw-event blob."""
    for key in _MITRE_NAME_KEYS:
        signals.mitre_names.extend(_as_string_list(document.get(key)))

    for key in _RULE_GROUP_KEYS:
        signals.rule_groups.extend(_as_string_list(document.get(key)))

    # MITRE ids can be under any of several key spellings, and are sometimes
    # only present inline in a description field. One regex sweep over every
    # scalar in the blob catches all of them without a key allow-list that
    # would need updating per source.
    scalars: List[str] = []
    _flatten_values(document, scalars)
    for scalar in scalars:
        signals.mitre_ids |= _extract_mitre_ids(scalar)


async def build_alert_signals(
    session: AsyncSession,
    alert: Optional[Alert] = None,
    customer_code: Optional[str] = None,
    source: Optional[str] = None,
) -> AlertSignals:
    """Collect scoring signals for an alert, or for a bare customer/source pair.

    Database reads only — tags plus the stored alert context. The raw
    originating event is a separate, opt-in step (``enrich_with_raw_event``)
    because it costs an indexer round-trip that most requests do not need.
    """
    signals = AlertSignals(
        customer_code=customer_code,
        source=source,
    )

    if alert is None:
        return signals

    signals.alert_id = alert.id
    signals.alert_name = alert.alert_name
    signals.customer_code = alert.customer_code
    signals.source = alert.source

    signals.tags = await _load_alert_tags(alert.id, session)

    context = await _load_alert_context(alert.id, session)
    if context:
        signals.document.update(context)
        signals.document_available = True
        _signals_from_document(signals, context)

    signals.keywords = [
        token
        for token in dict.fromkeys(_tokenize(alert.alert_name or ""))
        if len(token) >= _MIN_TOKEN_LENGTH and token not in _KEYWORD_STOPWORDS
    ]

    # De-duplicate while preserving order so the reasons read predictably.
    signals.mitre_names = list(dict.fromkeys(n.strip() for n in signals.mitre_names if n.strip()))
    signals.rule_groups = list(dict.fromkeys(g.strip() for g in signals.rule_groups if g.strip()))

    return signals


def unresolved_condition_fields(
    templates: Iterable[CaseTemplate],
    signals: AlertSignals,
) -> List[str]:
    """Which conditional ``match_field``s the stored context cannot settle.

    The stored alert context is a projection of the originating document
    through the operator's ingest field dictionary, so a template keyed on a
    field that dictionary drops is unresolvable from the database alone. Those
    — and only those — justify the indexer round-trip.
    """
    return sorted(
        {t.match_field for t in templates if t.match_field and t.match_value and t.match_field not in signals.document},
    )


async def enrich_with_raw_event(
    signals: AlertSignals,
    alert: Alert,
    session: AsyncSession,
) -> AlertSignals:
    """Merge the raw originating Wazuh document into ``signals``, in place.

    Reuses ``case_tasks._fetch_raw_event_for_alert`` rather than reimplementing
    the asset → (index_name, index_id) lookup, so suggestions read exactly the
    document auto-apply would evaluate against. That helper swallows its own
    failures and returns None, which leaves ``document_available`` as whatever
    the stored context set it to — the "unknown condition" state.
    """
    # Lazy import: case_tasks does not import this module today, but both are
    # service-layer modules in the same package and a module-level edge here is
    # exactly the shape that trips circular-import resolution later.
    from app.incidents.services.case_tasks import _fetch_raw_event_for_alert

    raw_event = await _fetch_raw_event_for_alert(alert, session)
    if not raw_event:
        return signals

    # Raw document wins on conflict — the stored context is a lossy projection
    # of it, so where they disagree the raw side is the more complete value.
    signals.document.update(raw_event)
    signals.document_available = True
    _signals_from_document(signals, raw_event)

    signals.mitre_names = list(dict.fromkeys(n.strip() for n in signals.mitre_names if n.strip()))
    signals.rule_groups = list(dict.fromkeys(g.strip() for g in signals.rule_groups if g.strip()))
    return signals


# ---------------------------------------------------------------------------
# Template corpus
# ---------------------------------------------------------------------------


@dataclass
class TemplateCorpus:
    """The searchable text of a template, precomputed once per scoring run."""

    text: str
    tokens: Set[str]
    mitre_ids: Set[str]


def build_template_corpus(template: CaseTemplate) -> TemplateCorpus:
    """Flatten a template's own words into something matchable.

    Task text is included, not just the template's name and description,
    because that is where the specifics live — a template named "Endpoint
    triage" whose tasks talk about ransomware and T1486 should rank on an
    encryption alert.
    """
    parts: List[str] = [template.name or "", template.description or ""]
    for task in template.tasks or []:
        parts.extend([task.title or "", task.description or "", task.guidelines or ""])

    text = " ".join(p for p in parts if p).lower()
    return TemplateCorpus(
        text=text,
        tokens=set(_tokenize(text)),
        mitre_ids=_extract_mitre_ids(text),
    )


# ---------------------------------------------------------------------------
# Usage history
# ---------------------------------------------------------------------------


async def load_usage_counts(
    session: AsyncSession,
    customer_code: Optional[str],
) -> Dict[int, int]:
    """How many distinct cases each template has been applied to.

    Counted through ``CaseTask.template_task_id`` rather than the
    ``template_applied`` timeline event, for two reasons: the join is plain
    relational SQL that behaves identically on MySQL and the SQLite fallback
    (``CaseEvent.payload`` is a JSON column and extracting from it is
    dialect-specific), and it measures templates whose tasks actually landed on
    a case rather than apply calls that added nothing.

    Scoped to ``customer_code`` when given — "what this customer's analysts
    reach for" is the useful signal; a deployment-wide count would just rank the
    biggest tenant's habits first. Templates whose source tasks have since been
    deleted drop out of the join; that is acceptable for a tiebreaker.
    """
    stmt = (
        select(CaseTemplateTask.template_id, func.count(func.distinct(CaseTask.case_id)))
        .join(CaseTask, CaseTask.template_task_id == CaseTemplateTask.id)
        .group_by(CaseTemplateTask.template_id)
    )
    if customer_code:
        stmt = stmt.join(Case, Case.id == CaseTask.case_id).where(Case.customer_code == customer_code)

    try:
        rows = (await session.execute(stmt)).all()
    except Exception as e:  # pragma: no cover - defensive; history is optional
        logger.warning(f"template suggestions: usage-history lookup failed, scoring without it: {e}")
        return {}

    return {template_id: count for template_id, count in rows if template_id is not None}


def _usage_points(count: int) -> int:
    """Log-scaled usage bonus, clamped to ``WEIGHT_USAGE_HISTORY_MAX``.

    ``log2(1 + count)`` reaches the cap around 8 applications, so a template
    used twice is meaningfully ahead of one never used, and one used fifty times
    is not meaningfully ahead of one used ten times.
    """
    if count <= 0:
        return 0
    return min(WEIGHT_USAGE_HISTORY_MAX, int(round(4 * math.log2(1 + count))))


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _confidence_for(score: int) -> str:
    if score >= CONFIDENCE_HIGH_THRESHOLD:
        return "high"
    if score >= CONFIDENCE_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _evaluate_condition(template: CaseTemplate, signals: AlertSignals) -> Optional[bool]:
    """Does this template's auto-apply condition hold?

    Returns True/False when the document was readable, and None when it was not
    — "unknown" is a third outcome the caller must not collapse into False, or
    a transient indexer outage would hide every conditional template.

    The comparison mirrors ``pick_templates_for_alert`` exactly, including the
    ``str()`` coercion: Wazuh quotes numeric top-level fields already, but not
    every source does.
    """
    if not template.match_field or not template.match_value:
        return None
    if not signals.document_available:
        return None

    doc_value = signals.document.get(template.match_field)
    if doc_value is None:
        return False
    return str(doc_value) == template.match_value


def _score_scope(
    template: CaseTemplate,
    signals: AlertSignals,
    reasons: List[SuggestionReason],
) -> int:
    score = 0
    if template.customer_code and signals.customer_code and template.customer_code == signals.customer_code:
        score += WEIGHT_CUSTOMER_MATCH
        reasons.append(
            SuggestionReason(
                signal="customer",
                detail=f"Scoped to customer {template.customer_code}",
                points=WEIGHT_CUSTOMER_MATCH,
            ),
        )
    if template.source and signals.source and template.source == signals.source:
        score += WEIGHT_SOURCE_MATCH
        reasons.append(
            SuggestionReason(
                signal="source",
                detail=f"Scoped to {template.source} alerts",
                points=WEIGHT_SOURCE_MATCH,
            ),
        )
    return score


def _score_tags(
    corpus: TemplateCorpus,
    signals: AlertSignals,
    reasons: List[SuggestionReason],
) -> int:
    """Alert tags matched against the template's own words.

    A tag that *is* a MITRE id is routed to the MITRE corpus instead of the text
    one — analysts do tag alerts ``T1566`` — so it matches a template that
    mentions the technique even if the literal string sits inside a sentence.
    """
    score = 0
    matched: List[str] = []
    for tag in signals.tags:
        mitre_in_tag = _extract_mitre_ids(tag)
        if mitre_in_tag:
            if mitre_in_tag & corpus.mitre_ids:
                matched.append(tag)
            continue
        if _contains_phrase(corpus.tokens, corpus.text, tag):
            matched.append(tag)

    if matched:
        score = min(CAP_TAG_MATCH, WEIGHT_TAG_MATCH * len(matched))
        reasons.append(
            SuggestionReason(
                signal="tag",
                detail=f"Matches alert tag(s): {', '.join(matched)}",
                points=score,
            ),
        )
    return score


def _score_mitre(
    corpus: TemplateCorpus,
    signals: AlertSignals,
    reasons: List[SuggestionReason],
) -> int:
    exact = sorted(signals.mitre_ids & corpus.mitre_ids)

    # Parent credit only for sub-techniques whose parent is named by the
    # template and whose exact id is not — otherwise T1059.001 would be counted
    # twice against a template naming both.
    parents: List[Tuple[str, str]] = []
    for technique_id in sorted(signals.mitre_ids):
        if technique_id in corpus.mitre_ids:
            continue
        parent = _mitre_parent(technique_id)
        if parent and parent in corpus.mitre_ids:
            parents.append((technique_id, parent))

    raw = WEIGHT_MITRE_MATCH * len(exact) + WEIGHT_MITRE_PARENT_MATCH * len(parents)
    score = min(CAP_MITRE_MATCH, raw)

    if exact:
        reasons.append(
            SuggestionReason(
                signal="mitre",
                detail=f"Covers MITRE technique(s): {', '.join(exact)}",
                points=min(CAP_MITRE_MATCH, WEIGHT_MITRE_MATCH * len(exact)),
            ),
        )
    if parents and score > 0:
        detail = ", ".join(f"{child} → {parent}" for child, parent in parents)
        reasons.append(
            SuggestionReason(
                signal="mitre_parent",
                detail=f"Covers the parent technique of: {detail}",
                points=max(0, score - min(CAP_MITRE_MATCH, WEIGHT_MITRE_MATCH * len(exact))),
            ),
        )

    # Technique / tactic display names are matched as plain text; they add no
    # points of their own (the ids already scored) but they do explain a match
    # to a reader who does not have the ATT&CK catalogue memorised.
    if not exact and not parents:
        named = [name for name in signals.mitre_names if _contains_phrase(corpus.tokens, corpus.text, name)]
        if named:
            score = min(CAP_MITRE_MATCH, WEIGHT_MITRE_PARENT_MATCH * len(named))
            reasons.append(
                SuggestionReason(
                    signal="mitre_name",
                    detail=f"Mentions MITRE technique(s): {', '.join(named)}",
                    points=score,
                ),
            )

    return score


def _score_rule_groups(
    corpus: TemplateCorpus,
    signals: AlertSignals,
    reasons: List[SuggestionReason],
) -> int:
    matched = [
        group
        for group in signals.rule_groups
        if group.lower() not in _GENERIC_RULE_GROUPS and _contains_phrase(corpus.tokens, corpus.text, group)
    ]
    if not matched:
        return 0
    score = min(CAP_RULE_GROUP_MATCH, WEIGHT_RULE_GROUP_MATCH * len(matched))
    reasons.append(
        SuggestionReason(
            signal="rule_group",
            detail=f"Matches rule group(s): {', '.join(matched)}",
            points=score,
        ),
    )
    return score


def _score_keywords(
    corpus: TemplateCorpus,
    signals: AlertSignals,
    reasons: List[SuggestionReason],
) -> int:
    matched = [keyword for keyword in signals.keywords if keyword in corpus.tokens]
    if not matched:
        return 0
    score = min(CAP_KEYWORD_MATCH, WEIGHT_KEYWORD_MATCH * len(matched))
    reasons.append(
        SuggestionReason(
            signal="keyword",
            detail=f"Alert title mentions: {', '.join(matched)}",
            points=score,
        ),
    )
    return score


def score_template(
    template: CaseTemplate,
    signals: AlertSignals,
    usage_counts: Dict[int, int],
    *,
    corpus: Optional[TemplateCorpus] = None,
) -> Tuple[int, List[SuggestionReason], Optional[bool]]:
    """Score one template. Returns ``(score, reasons, condition_result)``.

    ``condition_result`` is passed back so the caller can drop templates whose
    auto-apply condition was evaluated and failed — that is a filtering
    decision, not a scoring one.
    """
    corpus = corpus or build_template_corpus(template)
    reasons: List[SuggestionReason] = []
    score = 0

    condition_result = _evaluate_condition(template, signals)
    if condition_result is True:
        score += WEIGHT_CONDITION_MATCH
        reasons.append(
            SuggestionReason(
                signal="condition",
                detail=f"Auto-apply condition matches ({template.match_field} = {template.match_value})",
                points=WEIGHT_CONDITION_MATCH,
            ),
        )
    elif condition_result is None and template.match_field:
        reasons.append(
            SuggestionReason(
                signal="condition_unverified",
                detail=(f"Auto-apply condition on {template.match_field} could not be checked — " "the originating event was not readable"),
                points=0,
            ),
        )

    score += _score_scope(template, signals, reasons)
    score += _score_tags(corpus, signals, reasons)
    score += _score_mitre(corpus, signals, reasons)
    score += _score_rule_groups(corpus, signals, reasons)
    score += _score_keywords(corpus, signals, reasons)

    usage = usage_counts.get(template.id, 0)
    usage_points = _usage_points(usage)
    if usage_points:
        score += usage_points
        scope = f" for {signals.customer_code}" if signals.customer_code else ""
        reasons.append(
            SuggestionReason(
                signal="usage",
                detail=f"Applied to {usage} case(s){scope}",
                points=usage_points,
            ),
        )

    if template.is_default:
        score += WEIGHT_IS_DEFAULT
        reasons.append(
            SuggestionReason(
                signal="default",
                detail="Default template for its scope",
                points=WEIGHT_IS_DEFAULT,
            ),
        )

    return score, reasons, condition_result


# ---------------------------------------------------------------------------
# Candidate selection
# ---------------------------------------------------------------------------


def _in_scope(template: CaseTemplate, signals: AlertSignals) -> bool:
    """Is this template even applicable?

    Scope is a hard filter, not a penalty: a template pinned to customer B must
    never be offered on customer A's alert regardless of how well its text
    matches. Templates left NULL (global / any-source) always pass.

    A ``source`` filter is only applied when we know the alert's source. During
    manual case creation we do not, so every template stays a candidate and the
    source dimension simply contributes no points.
    """
    if template.customer_code and signals.customer_code and template.customer_code != signals.customer_code:
        return False
    if template.customer_code and not signals.customer_code:
        # Customer-scoped template, no customer context: cannot confirm it
        # applies. Excluding is the conservative side of the trade.
        return False
    if template.source and signals.source and template.source != signals.source:
        return False
    return True


async def _load_candidate_templates(session: AsyncSession) -> List[CaseTemplate]:
    stmt = select(CaseTemplate).options(selectinload(CaseTemplate.tasks))
    return list((await session.execute(stmt)).scalars().all())


async def suggest_templates(
    session: AsyncSession,
    *,
    alert_id: Optional[int] = None,
    customer_code: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = DEFAULT_SUGGESTION_LIMIT,
) -> CaseTemplateSuggestionListResponse:
    """Rank templates for the case an analyst is about to open.

    Two entry contexts, one code path:

    - **From an alert** (``alert_id``) — full topical scoring. ``customer_code``
      and ``source`` are taken from the alert itself; anything passed by the
      caller is ignored, because the alert is the authority on its own scope.
    - **Manual creation** (``customer_code`` and/or ``source``) — scope, usage
      history and ``is_default`` only. Still useful: it is the same ordering the
      analyst would get from the tier picker, but explained.

    Never raises for a missing alert or an empty template set — this feeds a
    panel that renders beside a form, and a failed suggestion lookup must not
    block case creation. Failures come back as ``success=False`` with an empty
    list.
    """
    try:
        alert: Optional[Alert] = None
        if alert_id is not None:
            alert = (await session.execute(select(Alert).where(Alert.id == alert_id))).scalars().first()
            if alert is None:
                return CaseTemplateSuggestionListResponse(
                    suggestions=[],
                    success=False,
                    message=f"Alert id={alert_id} not found",
                )

        # Signals first, from the database only. Scope filtering and scoring
        # then both read this one object, so they can never disagree about
        # which customer or source the case belongs to.
        signals = await build_alert_signals(
            session,
            alert=alert,
            customer_code=customer_code,
            source=source,
        )

        templates = await _load_candidate_templates(session)
        candidates = [t for t in templates if _in_scope(t, signals)]

        # Only pay for the indexer round-trip when an in-scope conditional
        # template keys on a field the stored context does not already carry.
        if alert is not None:
            unresolved = unresolved_condition_fields(candidates, signals)
            if unresolved:
                logger.debug(
                    f"template suggestions: fetching raw event for alert id={alert.id} to settle " f"condition field(s) {unresolved}",
                )
                signals = await enrich_with_raw_event(signals, alert, session)

        usage_counts = await load_usage_counts(session, signals.customer_code)

        suggestions: List[CaseTemplateSuggestion] = []
        for template in candidates:
            score, reasons, condition_result = score_template(template, signals, usage_counts)

            # A condition we checked and that came back false is the operator
            # saying "not this one". Drop it rather than ranking it low —
            # showing it invites an analyst to override a rule deliberately set.
            if condition_result is False:
                continue

            suggestions.append(
                CaseTemplateSuggestion(
                    # Reuse the list/CRUD serializer rather than validating the
                    # ORM row directly: it sorts tasks by order_index, which is
                    # the order the preview has to show them in.
                    template=_template_to_response(template),
                    score=score,
                    confidence=_confidence_for(score),
                    reasons=sorted(reasons, key=lambda r: r.points, reverse=True),
                ),
            )

        # Ties broken by is_default then name, so repeated calls return a stable
        # order — a list that reshuffles between renders reads as broken.
        suggestions.sort(key=lambda s: (-s.score, not s.template.is_default, s.template.name.lower()))
        top = suggestions[: max(0, limit)] if limit else suggestions

        return CaseTemplateSuggestionListResponse(
            suggestions=top,
            total_candidates=len(suggestions),
            success=True,
            message=f"Ranked {len(suggestions)} applicable template(s)",
        )

    except Exception as e:
        logger.error(f"Failed to build case template suggestions: {e}")
        return CaseTemplateSuggestionListResponse(
            suggestions=[],
            success=False,
            message=f"Failed to build case template suggestions: {e}",
        )


__all__ = (
    "AlertSignals",
    "TemplateCorpus",
    "build_alert_signals",
    "build_template_corpus",
    "enrich_with_raw_event",
    "load_usage_counts",
    "score_template",
    "suggest_templates",
    "unresolved_condition_fields",
)
