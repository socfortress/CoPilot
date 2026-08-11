"""Smart case-template suggestion ranking (issue #935).

The suggestion endpoint is advisory — it cannot corrupt anything — so what
these tests protect is not data integrity but *trust*: an analyst who is shown
a ranked list has to be able to rely on it. Concretely they pin:

- **Scope is a hard filter, never a penalty.** A template pinned to customer B
  must not surface on customer A's alert no matter how well its text matches.
  Getting this wrong leaks one tenant's playbook into another's console.
- **A checked-and-failed auto-apply condition drops the template.** The
  operator wrote that condition to mean "not this one"; ranking it low instead
  of removing it invites an analyst to override a deliberate rule. But an
  *unreadable* document is a third outcome — a transient indexer outage must
  not silently hide every conditional template.
- **The reasons sum to the score.** The UI renders reason chips as the
  explanation for the ranking; if they don't add up, the explanation is a lie.
- **Ordering is stable.** A list that reshuffles between renders reads as
  broken even when every score is right.

Unit tests with mocked sessions — no real DB, no indexer.

Run with: cd backend && python -m pytest tests/test_case_template_suggestions.py
"""

import asyncio
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import app.incidents.services.template_suggestions as svc  # noqa: E402
from app.incidents.services.template_suggestions import AlertSignals  # noqa: E402

NOW = datetime(2026, 1, 1, 12, 0, 0)


# ---------------------------------------------------------------------------
# Fixtures-as-builders
# ---------------------------------------------------------------------------


def _task(title, description=None, guidelines=None, order_index=0, task_id=1):
    return SimpleNamespace(
        id=task_id,
        template_id=1,
        title=title,
        description=description,
        guidelines=guidelines,
        mandatory=False,
        order_index=order_index,
    )


def _template(
    template_id=1,
    name="Generic triage",
    description=None,
    customer_code=None,
    source=None,
    is_default=False,
    match_field=None,
    match_value=None,
    tasks=None,
):
    return SimpleNamespace(
        id=template_id,
        name=name,
        description=description,
        customer_code=customer_code,
        source=source,
        is_default=is_default,
        match_field=match_field,
        match_value=match_value,
        created_by="admin",
        created_at=NOW,
        updated_at=NOW,
        tasks=tasks if tasks is not None else [],
    )


def _signals(**kwargs):
    kwargs.setdefault("customer_code", "ACME")
    kwargs.setdefault("source", "wazuh")
    return AlertSignals(**kwargs)


def _score(template, signals=None, usage=None):
    """Score one template, returning (score, reasons, condition_result)."""
    return svc.score_template(template, signals or _signals(), usage or {})


def _signal_keys(reasons):
    return {r.signal for r in reasons}


# ---------------------------------------------------------------------------
# Scope filtering — the tenancy-relevant half
# ---------------------------------------------------------------------------


def test_template_for_another_customer_is_out_of_scope():
    """The leak case. A well-matching template still must not cross tenants."""
    template = _template(customer_code="OTHERCO", name="Ransomware containment")
    assert svc._in_scope(template, _signals(customer_code="ACME")) is False


def test_global_template_is_in_scope_for_every_customer():
    assert svc._in_scope(_template(customer_code=None), _signals(customer_code="ACME")) is True


def test_customer_scoped_template_excluded_without_customer_context():
    """Manual creation before a customer is picked: we cannot confirm it applies."""
    template = _template(customer_code="ACME")
    assert svc._in_scope(template, AlertSignals(customer_code=None, source=None)) is False


def test_source_mismatch_is_out_of_scope():
    template = _template(source="office365")
    assert svc._in_scope(template, _signals(source="wazuh")) is False


def test_source_scoped_template_stays_in_scope_when_source_unknown():
    """Manual creation has no alert source; the dimension just scores nothing."""
    template = _template(source="wazuh")
    assert svc._in_scope(template, AlertSignals(customer_code="ACME", source=None)) is True


def test_scope_matches_award_their_weights():
    template = _template(customer_code="ACME", source="wazuh")
    score, reasons, _ = _score(template)
    assert score == svc.WEIGHT_CUSTOMER_MATCH + svc.WEIGHT_SOURCE_MATCH
    assert _signal_keys(reasons) == {"customer", "source"}


# ---------------------------------------------------------------------------
# Auto-apply conditions
# ---------------------------------------------------------------------------


def test_satisfied_condition_scores_and_survives():
    template = _template(match_field="data_win_system_eventID", match_value="1")
    signals = _signals(document={"data_win_system_eventID": "1"}, document_available=True)
    score, reasons, condition = _score(template, signals)

    assert condition is True
    assert score >= svc.WEIGHT_CONDITION_MATCH
    assert "condition" in _signal_keys(reasons)


def test_failed_condition_is_reported_so_the_caller_can_drop_it():
    template = _template(match_field="data_win_system_eventID", match_value="1")
    signals = _signals(document={"data_win_system_eventID": "4688"}, document_available=True)
    _, _, condition = _score(template, signals)
    assert condition is False


def test_absent_field_counts_as_a_failed_condition():
    """The field the operator keyed on simply isn't on this event."""
    template = _template(match_field="data_win_system_eventID", match_value="1")
    signals = _signals(document={"rule_id": "5710"}, document_available=True)
    _, _, condition = _score(template, signals)
    assert condition is False


def test_unreadable_document_leaves_the_condition_unknown_not_false():
    """An indexer outage must not silently hide every conditional template."""
    template = _template(match_field="data_win_system_eventID", match_value="1")
    signals = _signals(document={}, document_available=False)
    score, reasons, condition = _score(template, signals)

    assert condition is None
    assert "condition_unverified" in _signal_keys(reasons)
    # Unverified earns nothing — it explains, it does not promote. (The template
    # here is global/any-source, so scope contributes nothing either.)
    assert score == 0


def test_numeric_document_values_are_coerced_like_the_auto_apply_path():
    """Not every source quotes its numerics the way Wazuh does."""
    template = _template(match_field="event_id", match_value="4625")
    signals = _signals(document={"event_id": 4625}, document_available=True)
    _, _, condition = _score(template, signals)
    assert condition is True


def test_suggest_drops_templates_whose_condition_was_checked_and_failed():
    templates = [
        _template(template_id=1, name="Sysmon proc create", match_field="event_id", match_value="1"),
        _template(template_id=2, name="Generic triage"),
    ]
    response = _run_suggest(
        templates=templates,
        signals=_signals(document={"event_id": "4688"}, document_available=True),
    )
    assert [s.template.id for s in response.suggestions] == [2]


def test_suggest_keeps_conditional_templates_when_the_document_is_unreadable():
    templates = [_template(template_id=1, name="Sysmon proc create", match_field="event_id", match_value="1")]
    response = _run_suggest(
        templates=templates,
        signals=_signals(document={}, document_available=False),
    )
    assert [s.template.id for s in response.suggestions] == [1]


# ---------------------------------------------------------------------------
# Topical signals
# ---------------------------------------------------------------------------


def test_alert_tag_matches_template_task_text():
    """Task text is part of the corpus — that's where the specifics live."""
    template = _template(
        name="Endpoint triage",
        tasks=[_task("Isolate host", description="Suspected ransomware encryption activity")],
    )
    score, reasons, _ = _score(template, _signals(tags=["ransomware"]))
    assert score == svc.WEIGHT_TAG_MATCH
    assert "tag" in _signal_keys(reasons)


def test_tag_separators_are_normalised():
    """``lateral-movement`` and ``lateral movement`` are the same tag."""
    template = _template(name="Lateral movement playbook")
    score, _, _ = _score(template, _signals(tags=["lateral-movement"]))
    assert score == svc.WEIGHT_TAG_MATCH


def test_multi_word_tag_requires_word_order():
    template = _template(name="Movement lateral of files")
    score, _, _ = _score(template, _signals(tags=["lateral movement"]))
    assert score == 0


def test_tag_scoring_is_capped():
    template = _template(name="phishing ransomware exfiltration persistence privilege")
    tags = ["phishing", "ransomware", "exfiltration", "persistence", "privilege"]
    score, reasons, _ = _score(template, _signals(tags=tags))
    assert score == svc.CAP_TAG_MATCH
    assert next(r for r in reasons if r.signal == "tag").points == svc.CAP_TAG_MATCH


def test_a_mitre_id_tag_is_matched_against_the_technique_corpus():
    """Analysts do tag alerts ``T1566`` — route those to MITRE, not free text."""
    template = _template(
        name="Phishing response",
        tasks=[_task("Review mail", description="Covers T1566 phishing delivery")],
    )
    score, reasons, _ = _score(template, _signals(tags=["T1566"]))
    assert "tag" in _signal_keys(reasons)
    assert score >= svc.WEIGHT_TAG_MATCH


def test_exact_mitre_technique_match():
    template = _template(name="Script interpreter abuse", description="Handles T1059.001")
    score, reasons, _ = _score(template, _signals(mitre_ids={"T1059.001"}))
    assert score == svc.WEIGHT_MITRE_MATCH
    assert "mitre" in _signal_keys(reasons)


def test_parent_technique_earns_partial_credit_only():
    """T1059 named by the template, T1059.001 on the alert: related, less precise."""
    template = _template(name="Command interpreter abuse", description="Handles T1059")
    score, reasons, _ = _score(template, _signals(mitre_ids={"T1059.001"}))
    assert score == svc.WEIGHT_MITRE_PARENT_MATCH
    assert "mitre_parent" in _signal_keys(reasons)
    assert svc.WEIGHT_MITRE_PARENT_MATCH < svc.WEIGHT_MITRE_MATCH


def test_parent_credit_is_not_double_counted_with_an_exact_match():
    template = _template(description="Handles T1059 and T1059.001")
    score, _, _ = _score(template, _signals(mitre_ids={"T1059.001"}))
    assert score == svc.WEIGHT_MITRE_MATCH


def test_mitre_display_names_match_when_no_id_does():
    template = _template(name="Command and Scripting Interpreter response")
    score, reasons, _ = _score(
        template,
        _signals(mitre_names=["Command and Scripting Interpreter"]),
    )
    assert score == svc.WEIGHT_MITRE_PARENT_MATCH
    assert "mitre_name" in _signal_keys(reasons)


def test_mitre_ids_are_case_insensitive():
    template = _template(description="covers t1486")
    score, _, _ = _score(template, _signals(mitre_ids={"T1486"}))
    assert score == svc.WEIGHT_MITRE_MATCH


def test_generic_rule_groups_are_ignored():
    """Matching on ``syslog`` or ``pci_dss`` would fire on everything."""
    template = _template(name="Syslog and pci_dss and wazuh review")
    score, _, _ = _score(template, _signals(rule_groups=["syslog", "pci_dss", "wazuh"]))
    assert score == 0


def test_meaningful_rule_group_scores():
    template = _template(name="Windows authentication failures")
    score, reasons, _ = _score(template, _signals(rule_groups=["authentication_failures"]))
    assert score == svc.WEIGHT_RULE_GROUP_MATCH
    assert "rule_group" in _signal_keys(reasons)


def test_alert_title_stopwords_do_not_score():
    """ "suspicious", "detected", "rule" appear in half of all alert titles."""
    template = _template(name="Suspicious activity detected rule")
    signals = _signals(keywords=[])  # what build_alert_signals would produce
    score, _, _ = _score(template, signals)
    assert score == 0


def test_title_keyword_match_scores():
    template = _template(name="Mimikatz credential dumping")
    score, reasons, _ = _score(template, _signals(keywords=["mimikatz"]))
    assert score == svc.WEIGHT_KEYWORD_MATCH
    assert "keyword" in _signal_keys(reasons)


# ---------------------------------------------------------------------------
# Usage history and defaults
# ---------------------------------------------------------------------------


def test_usage_points_are_log_scaled_and_capped():
    assert svc._usage_points(0) == 0
    assert svc._usage_points(1) > 0
    assert svc._usage_points(2) > svc._usage_points(1)
    assert svc._usage_points(50) == svc.WEIGHT_USAGE_HISTORY_MAX
    # Diminishing returns is the whole point: without it the most-applied
    # template becomes self-reinforcing and nothing new ever surfaces.
    assert (svc._usage_points(6) - svc._usage_points(5)) < (svc._usage_points(2) - svc._usage_points(1))


def test_usage_history_never_outranks_scope():
    """A heavily-used global template must not beat a correctly-scoped one."""
    heavily_used = _template(template_id=1, name="Everything template")
    scoped = _template(template_id=2, name="Scoped", customer_code="ACME", source="wazuh")

    used_score, _, _ = _score(heavily_used, usage={1: 500})
    scoped_score, _, _ = _score(scoped, usage={})
    assert scoped_score > used_score


def test_default_flag_contributes_its_weight():
    score, reasons, _ = _score(_template(is_default=True))
    assert score == svc.WEIGHT_IS_DEFAULT
    assert "default" in _signal_keys(reasons)


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "template,signals",
    [
        (
            _template(customer_code="ACME", source="wazuh", is_default=True, description="T1486 ransomware"),
            _signals(tags=["ransomware"], mitre_ids={"T1486"}, keywords=["ransomware"]),
        ),
        (
            _template(name="Phishing", tasks=[_task("Check headers", guidelines="T1566.001 delivery")]),
            _signals(tags=["phishing"], mitre_ids={"T1566.001"}, rule_groups=["email"]),
        ),
        (
            _template(match_field="event_id", match_value="1", name="Sysmon"),
            _signals(document={"event_id": "1"}, document_available=True, tags=["sysmon"]),
        ),
    ],
)
def test_reasons_always_sum_to_the_score(template, signals):
    """The UI shows reasons as *the* explanation. They have to add up."""
    score, reasons, _ = _score(template, signals, usage={template.id: 4})
    assert sum(r.points for r in reasons) == score


def test_confidence_buckets_track_the_thresholds():
    assert svc._confidence_for(svc.CONFIDENCE_HIGH_THRESHOLD) == "high"
    assert svc._confidence_for(svc.CONFIDENCE_HIGH_THRESHOLD - 1) == "medium"
    assert svc._confidence_for(svc.CONFIDENCE_MEDIUM_THRESHOLD) == "medium"
    assert svc._confidence_for(svc.CONFIDENCE_MEDIUM_THRESHOLD - 1) == "low"


# ---------------------------------------------------------------------------
# The endpoint service
# ---------------------------------------------------------------------------


def _run_suggest(templates, signals, usage=None, limit=5, alert=None, **kwargs):
    """Drive suggest_templates with every DB read stubbed out.

    ``build_alert_signals`` is replaced wholesale, so the ``signals`` passed in
    is the single object both scope filtering and scoring see — which is
    exactly the invariant the production code now holds.
    """
    session = AsyncMock()

    # The only unstubbed session.execute left is the alert lookup.
    result = SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: alert))
    session.execute = AsyncMock(return_value=result)

    async def _fake_signals(*_args, **_kwargs):
        return signals

    async def _fake_usage(*_args, **_kwargs):
        return usage or {}

    with (
        patch.object(svc, "_load_candidate_templates", AsyncMock(return_value=templates)),
        patch.object(svc, "build_alert_signals", _fake_signals),
        patch.object(svc, "load_usage_counts", _fake_usage),
        patch.object(svc, "enrich_with_raw_event", AsyncMock(return_value=signals)),
    ):
        return asyncio.run(
            svc.suggest_templates(session=session, limit=limit, **kwargs),
        )


def test_suggestions_are_ranked_best_first():
    templates = [
        _template(template_id=1, name="Generic triage"),
        _template(template_id=2, name="Ransomware containment", customer_code="ACME", source="wazuh"),
        _template(template_id=3, name="Phishing response"),
    ]
    response = _run_suggest(templates=templates, signals=_signals(tags=["ransomware"]))

    assert response.success is True
    assert response.suggestions[0].template.id == 2
    assert response.total_candidates == 3


def test_out_of_scope_templates_never_reach_the_response():
    templates = [
        _template(template_id=1, name="Other tenant ransomware", customer_code="OTHERCO"),
        _template(template_id=2, name="Generic triage"),
    ]
    response = _run_suggest(templates=templates, signals=_signals(tags=["ransomware"]))
    assert [s.template.id for s in response.suggestions] == [2]


def test_limit_trims_the_list_but_total_candidates_reports_the_truth():
    templates = [_template(template_id=i, name=f"Template {i}") for i in range(1, 8)]
    response = _run_suggest(templates=templates, signals=_signals(), limit=3)
    assert len(response.suggestions) == 3
    assert response.total_candidates == 7


def test_ordering_is_stable_across_identical_scores():
    """Ties break on is_default then name, so renders don't reshuffle."""
    templates = [
        _template(template_id=1, name="Zebra"),
        _template(template_id=2, name="Alpha"),
        _template(template_id=3, name="Middle", is_default=False),
    ]
    first = _run_suggest(templates=templates, signals=_signals())
    second = _run_suggest(templates=list(reversed(templates)), signals=_signals())
    assert [s.template.id for s in first.suggestions] == [s.template.id for s in second.suggestions]
    assert [s.template.name for s in first.suggestions] == ["Alpha", "Middle", "Zebra"]


def test_default_wins_a_tie_against_a_non_default():
    templates = [
        _template(template_id=1, name="Alpha"),
        _template(template_id=2, name="Zebra", is_default=True),
    ]
    response = _run_suggest(templates=templates, signals=_signals())
    assert response.suggestions[0].template.id == 2


def test_a_firing_condition_outranks_a_higher_scoring_template():
    """The partition, not a weight — this is what keeps the panel agreeing with
    ``pick_templates_for_alert``, where field-match templates win outright and
    the scope-tier picker only runs when none of them fire.

    Regression: expressing this as a 40-point weight let a template scoring
    customer (25) + source (20) beat a firing condition, so the panel
    recommended something different from what auto-apply would have applied.
    Caught by the e2e, not by the mocked tests.
    """
    templates = [
        _template(template_id=1, name="Well scoped", customer_code="ACME", source="wazuh"),
        _template(template_id=2, name="Conditional", match_field="event_id", match_value="1"),
    ]
    signals = _signals(document={"event_id": "1"}, document_available=True, tags=["ransomware"])
    response = _run_suggest(templates=templates, signals=signals)

    top, second = response.suggestions[0], response.suggestions[1]
    assert top.template.id == 2
    assert top.condition_matched is True
    # The point of the partition: it wins despite scoring less.
    assert top.score < second.score
    assert second.condition_matched is False


def test_condition_matched_is_false_when_the_document_is_unreadable():
    """Unverified is not matched — it must not jump the queue."""
    templates = [_template(template_id=1, match_field="event_id", match_value="1")]
    response = _run_suggest(
        templates=templates,
        signals=_signals(document={}, document_available=False),
    )
    assert response.suggestions[0].condition_matched is False


def test_suggestion_carries_the_full_task_list_for_the_preview():
    """One round-trip: the preview must not need a second call per suggestion."""
    templates = [
        _template(
            template_id=1,
            tasks=[
                _task("Second", order_index=1, task_id=20),
                _task("First", order_index=0, task_id=10),
            ],
        ),
    ]
    response = _run_suggest(templates=templates, signals=_signals())
    titles = [t.title for t in response.suggestions[0].template.tasks]
    assert titles == ["First", "Second"]


def test_missing_alert_reports_failure_without_raising():
    response = _run_suggest(templates=[], signals=_signals(), alert=None, alert_id=999)
    assert response.success is False
    assert "not found" in response.message


def test_a_lookup_failure_degrades_instead_of_blocking_case_creation():
    """This feeds a panel beside a form. It must never take the form down."""
    session = AsyncMock()
    with patch.object(svc, "_load_candidate_templates", AsyncMock(side_effect=RuntimeError("db down"))):
        response = asyncio.run(svc.suggest_templates(session=session))

    assert response.success is False
    assert response.suggestions == []


def test_manual_creation_path_still_ranks_on_scope_and_defaults():
    """No alert: topical signals are empty, scope and default still order things."""
    templates = [
        _template(template_id=1, name="Global fallback", is_default=True),
        _template(template_id=2, name="ACME playbook", customer_code="ACME"),
    ]
    response = _run_suggest(
        templates=templates,
        signals=AlertSignals(customer_code="ACME", source=None),
        customer_code="ACME",
    )
    assert response.suggestions[0].template.id == 2


# ---------------------------------------------------------------------------
# Corpus + context extraction helpers
# ---------------------------------------------------------------------------


def test_corpus_includes_name_description_and_all_task_text():
    template = _template(
        name="Alpha",
        description="Beta",
        tasks=[_task("Gamma", description="Delta", guidelines="Epsilon T1005")],
    )
    corpus = svc.build_template_corpus(template)
    for token in ("alpha", "beta", "gamma", "delta", "epsilon"):
        assert token in corpus.tokens
    assert corpus.mitre_ids == {"T1005"}


def test_context_values_are_flattened_regardless_of_shape():
    """Ingest writes these blobs straight through; shape varies by deployment."""
    signals = AlertSignals()
    svc._signals_from_document(signals, {"rule_groups": "windows,sysmon", "rule_mitre_id": ["T1059", "T1055"]})
    assert set(signals.rule_groups) == {"windows", "sysmon"}
    assert signals.mitre_ids == {"T1059", "T1055"}


def test_mitre_ids_are_found_even_when_only_inline_in_a_description():
    signals = AlertSignals()
    svc._signals_from_document(signals, {"rule_description": "Mimikatz detected (T1003.001)"})
    assert signals.mitre_ids == {"T1003.001"}


def test_no_indexer_call_when_the_stored_context_settles_every_condition():
    """The round-trip is the expensive part; the DB usually already has the field."""
    templates = [_template(match_field="event_id", match_value="1")]
    signals = _signals(document={"event_id": "1"}, document_available=True)
    assert svc.unresolved_condition_fields(templates, signals) == []


def test_indexer_call_is_gated_on_fields_the_ingest_dictionary_dropped():
    templates = [
        _template(template_id=1, match_field="data_win_eventdata_image", match_value="x"),
        _template(template_id=2, match_field="event_id", match_value="1"),
        _template(template_id=3),  # unconditional — never justifies a fetch
    ]
    signals = _signals(document={"event_id": "1"}, document_available=True)
    assert svc.unresolved_condition_fields(templates, signals) == ["data_win_eventdata_image"]


def test_half_set_match_pairs_never_trigger_a_fetch():
    """A match_field with no match_value is inert; it must not cost a round-trip."""
    templates = [_template(match_field="event_id", match_value=None)]
    assert svc.unresolved_condition_fields(templates, _signals(document={})) == []


def test_alert_context_merge_prefers_the_lowest_asset_id():
    """Divergent contexts across assets: first row wins, matching auto-apply."""
    session = AsyncMock()
    result = AsyncMock()
    result.scalars = lambda: SimpleNamespace(
        all=lambda: [{"rule_id": "100", "shared": "a"}, {"rule_id": "200", "extra": "b"}],
    )
    session.execute = AsyncMock(return_value=result)

    merged = asyncio.run(svc._load_alert_context(1, session))
    assert merged["rule_id"] == "100"
    assert merged["extra"] == "b"
