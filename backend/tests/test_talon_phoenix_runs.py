"""The run view, the Phoenix client and the "Talon Phoenix" connector (plan M5-9a; talon-analyst SPEC
§5.4 FR-PHX-1/2, D51, decisions A, E and F).

Real routers, a real in-memory database; Phoenix 20.20 as an ``httpx.MockTransport`` under the real
Phoenix client (``tests/talon_v2_support.py``), which asserts every request it gets is a GET.
Pinned here:
- authorization from CoPilot's own job and alert rows on every request, before any Phoenix call:
  another customer, an alert outside the caller's tags, an unknown job or a job whose alert is
  another customer's are refused with no Phoenix request at all;
- the project: ``talon-<code>`` only for a code talon-analyst's ``project_for`` routes there
  (M5-9t: the customer grammar, so a dotted code has its own project); ``talon-chat``, and a code
  talon-analyst sends there (``chat`` in any letter case, ``_x``), are never queried (409);
- the query: JSON-quoted ``job_id`` and ``customer_code`` filters, the time window, the sort, the
  page size; paging by cursor, at most 10 pages, ``truncated``; the 16 MB page cap;
- every span re-checked (another job's or customer's is dropped and counted);
- the allowlist: a marker planted in inputs, outputs, messages, ``status_message``, events,
  ``talon.scrub_*`` and a model-written tool name never reaches the response bytes, whose keys are
  exactly the DTO's;
- the viewer key: no run view, and no span read, unless ``GET /v1/user`` says VIEWER; the answer
  cached and keyed on the connector;
- Phoenix's text is never relayed and the key never logged; the busy 503;
- the connector's seed row and its check.

Run with: cd backend && python -m pytest tests/test_talon_phoenix_runs.py
"""

import asyncio
import json
import time
import tracemalloc
from datetime import datetime
from datetime import timedelta

import httpx
import pytest
from loguru import logger

from app.connectors.services import TalonPhoenixService
from app.connectors.services import get_connector_service
from app.connectors.talon.schema.talon_runs import RunTimeline
from app.connectors.talon.schema.talon_runs import TimelineSpan
from app.connectors.talon.services import talon_runs
from app.connectors.talon.utils import phoenix_client
from app.db import db_populate
from tests.talon_v2_support import ACME
from tests.talon_v2_support import CHAT
from tests.talon_v2_support import COMPLETED
from tests.talon_v2_support import CREATED
from tests.talon_v2_support import DOTTED
from tests.talon_v2_support import GLOBEX
from tests.talon_v2_support import JOB_ACME
from tests.talon_v2_support import JOB_CHAT
from tests.talon_v2_support import JOB_DOTTED
from tests.talon_v2_support import JOB_GLOBEX
from tests.talon_v2_support import JOB_MISMATCH
from tests.talon_v2_support import JOB_RUNNING
from tests.talon_v2_support import PHOENIX_KEY
from tests.talon_v2_support import PHOENIX_URL
from tests.talon_v2_support import Phoenix
from tests.talon_v2_support import RawStream
from tests.talon_v2_support import as_user
from tests.talon_v2_support import bomb_response
from tests.talon_v2_support import call
from tests.talon_v2_support import deeply_nested
from tests.talon_v2_support import phoenix_connector
from tests.talon_v2_support import restrict_tags
from tests.talon_v2_support import span
from tests.talon_v2_support import stacked_gzip

MARKER = "PLANTED-MARKER-7f3a"
SPAN_KEYS = set(TimelineSpan.model_fields)
TOP_KEYS = set(RunTimeline.model_fields)


def timeline(job=JOB_ACME):
    return f"/talon/v2/runs/{job}/timeline"


def get_timeline(who="ana", job=JOB_ACME):
    async def scenario(client, ctx):
        return await client.get(timeline(job), headers=as_user(who)), ctx

    return scenario


# ── authorization first ───────────────────────────────────────────────────────


def test_an_analyst_sees_their_customers_run():
    response, ctx = call(get_timeline())
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == TOP_KEYS
    assert (body["job_id"], body["customer_code"], body["truncated"], body["dropped"], body["note"]) == (JOB_ACME, ACME, False, 0, None)
    (only,) = body["spans"]
    assert only["name"] == "chat claude-sonnet-5-5" and only["kind"] == "LLM" and only["duration_ms"] == 60500
    assert (only["prompt_tokens"], only["completion_tokens"], only["total_tokens"]) == (1200, 300, 1500)
    assert (only["stage"], only["role"], only["model"]) == ("S5", "analyst", "claude-sonnet-5-5")
    assert only["start_time"] == "2026-10-16T08:00:00.000000Z"
    assert [r.url.path for r in ctx.phoenix.requests] == ["/v1/user", f"/v1/projects/talon-{ACME}/spans"]


@pytest.mark.parametrize("who", ["admin", "resp"])
def test_an_admin_and_a_responder_see_it_too(who):
    response, _ = call(get_timeline(who))
    assert response.status_code == 200


@pytest.mark.parametrize(
    "who, job",
    [
        ("ana", JOB_GLOBEX),  # another customer's job
        ("gus", JOB_ACME),
        ("ana", "copilot-inv-9-0"),  # unknown
        ("ana", JOB_ACME.upper()),
        ("ana", JOB_MISMATCH),  # the job says ACME; its alert is GLOBEX's
        ("admin", JOB_MISMATCH),
        ("ana", "y" * 65),
    ],
)
def test_a_run_the_caller_may_not_see_is_refused_with_no_phoenix_request(who, job):
    response, ctx = call(get_timeline(who, job))
    assert (response.status_code, response.json()) == (404, {"detail": "investigation not found"})
    assert response.headers["cache-control"] == "no-store"
    assert ctx.phoenix.requests == []


def test_an_alert_outside_the_callers_tags_is_refused_with_no_phoenix_request():
    async def scenario(client, ctx):
        await restrict_tags(ctx, ctx.acme_alert)
        return await client.get(timeline(), headers=as_user("ana")), ctx

    response, ctx = call(scenario)
    assert response.status_code == 404 and ctx.phoenix.requests == []


def test_the_customer_is_rechecked_on_every_request():
    async def scenario(client, ctx):
        first = await client.get(timeline(), headers=as_user("resp"))
        from sqlalchemy import delete

        from app.auth.models.users import UserCustomerAccess

        async with ctx.db.session() as session:
            await session.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == 5))
            await session.commit()
        before = len(ctx.phoenix.requests)
        second = await client.get(timeline(), headers=as_user("resp"))
        return first.status_code, second.status_code, len(ctx.phoenix.requests) - before

    assert call(scenario) == (200, 404, 0)


@pytest.mark.parametrize("who", ["portal", "sched"])
def test_portal_users_and_the_scheduler_are_refused(who):
    response, ctx = call(get_timeline(who))
    assert response.status_code == 403 and ctx.phoenix.requests == []


@pytest.mark.parametrize("enabled", [None, False])
def test_with_the_setting_off_the_run_view_is_not_found(enabled):
    async def scenario(client, ctx):
        return await client.get(timeline(), headers=as_user("admin")), ctx

    response, ctx = call(scenario, enabled=enabled)
    assert (response.status_code, response.json()) == (404, {"detail": "Not Found"})
    assert ctx.phoenix.requests == []


# ── the project ───────────────────────────────────────────────────────────────


def test_talon_chat_is_never_queried():
    phoenix = Phoenix(projects=(f"talon-{ACME}", "talon-chat", f"talon-{DOTTED}"))
    response, ctx = call(get_timeline("ana", JOB_CHAT), phoenix=phoenix)
    assert (response.status_code, response.json()) == (409, {"detail": talon_runs.NO_PROJECT})
    assert response.headers["cache-control"] == "no-store"
    assert ctx.phoenix.requests == []


def test_a_dotted_code_is_read_from_its_own_project():
    # talon-analyst M5-9t: ``project_for`` follows the customer grammar, so ``acme.io`` traces to
    # ``talon-acme.io`` (decision F's refusal is over).
    phoenix = Phoenix(projects=(f"talon-{ACME}", "talon-chat", f"talon-{DOTTED}"), pages=[[span(JOB_DOTTED, DOTTED)]])
    response, ctx = call(get_timeline("ana", JOB_DOTTED), phoenix=phoenix)
    assert response.status_code == 200
    assert (response.json()["customer_code"], len(response.json()["spans"])) == (DOTTED, 1)
    (spans_request,) = ctx.phoenix.span_requests()
    assert spans_request.url.path == f"/v1/projects/talon-{DOTTED}/spans"


@pytest.mark.parametrize(
    "code, project",
    [
        ("ACME", "talon-ACME"),
        ("lab_canary-2", "talon-lab_canary-2"),
        ("acme.io", "talon-acme.io"),  # talon-analyst M5-9t routes dotted codes
        ("a.b_c-d", "talon-a.b_c-d"),
        ("9lives", "talon-9lives"),
        ("a" * 64, "talon-" + "a" * 64),
        ("chat", None),  # its spans would share the chat project
        ("Chat", None),  # chat in any letter case goes to talon-chat
        ("CHAT", None),
        ("chat.io", "talon-chat.io"),
        ("_x", None),  # the grammar starts with a letter or digit
        ("-x", None),
        (".x", None),
        ("acme\n", None),  # re.match with $ would let this through
        (" acme", None),
        ("acme io", None),
        ("talon chat memory", None),  # the chat-memory wing
        ("TALON CHAT MEMORY", None),
        ("", None),
        ("a" * 65, None),
        ("a/b", None),
        ("a?b", None),
        ("a#b", None),
        ("acm\u00e9", None),  # ASCII only
        ("acme\u200b", None),  # a zero-width space
        (None, None),
        (7, None),
    ],
)
def test_the_project_follows_talon_analysts_project_for_rule(code, project):
    assert talon_runs.project_for(code) == project


def test_the_project_name_comes_from_the_job_never_the_request():
    async def scenario(client, ctx):
        await client.get(timeline() + f"?project=talon-{GLOBEX}&customer_code={GLOBEX}", headers=as_user("ana"))
        return ctx

    ctx = call(scenario)
    (spans_request,) = ctx.phoenix.span_requests()
    assert spans_request.url.path == f"/v1/projects/talon-{ACME}/spans"
    assert GLOBEX not in str(spans_request.url)


# ── the query ─────────────────────────────────────────────────────────────────


def test_the_query_is_json_quoted_filters_the_window_and_the_sort():
    response, ctx = call(get_timeline())
    (sent,) = ctx.phoenix.span_requests()
    params = sent.url.params
    assert params.get_list("attribute") == [f'job_id:"{JOB_ACME}"', f'customer_code:"{ACME}"']
    assert params["start_time"] == "2026-10-16T07:58:00Z"  # created_at - 2 min
    assert params["end_time"] == "2026-10-16T08:20:30Z"  # completed_at + 15 min
    assert (params["sort"], params["order"], params["limit"]) == ("start_time", "asc", "100")
    assert "cursor" not in params
    assert sent.headers["authorization"] == f"Bearer {PHOENIX_KEY}"


def test_a_running_jobs_window_ends_after_now():
    job = talon_runs.JobFacts(job_id=JOB_RUNNING, customer_code=ACME, created_at=CREATED, completed_at=None)
    start, end = talon_runs.time_window(job, now=datetime(2026, 10, 16, 9, 0, 0))
    assert (start, end) == ("2026-10-16T07:58:00Z", "2026-10-16T09:15:00Z")
    done = talon_runs.JobFacts(job_id=JOB_ACME, customer_code=ACME, created_at=CREATED, completed_at=COMPLETED)
    assert talon_runs.time_window(done) == ("2026-10-16T07:58:00Z", "2026-10-16T08:20:30Z")


def test_an_id_that_looks_like_json_is_still_one_quoted_string():
    job = talon_runs.JobFacts(job_id='a"b\\c', customer_code=ACME, created_at=CREATED, completed_at=COMPLETED)
    attribute = dict(talon_runs.span_query(job))["attribute"]  # the last one: customer_code
    first = talon_runs.span_query(job)[0][1]
    assert json.loads(first.split(":", 1)[1]) == 'a"b\\c' and json.loads(attribute.split(":", 1)[1]) == ACME


def test_pages_are_followed_by_cursor():
    pages = [[span(n=0), span(n=1)], [span(n=2)], [span(n=3)]]
    response, ctx = call(get_timeline(), phoenix=Phoenix(pages=pages))
    body = response.json()
    assert len(body["spans"]) == 4 and body["truncated"] is False
    assert [r.url.params.get("cursor") for r in ctx.phoenix.span_requests()] == [None, "c1", "c2"]


def test_at_most_ten_pages_are_read_and_the_rest_is_truncated():
    pages = [[span(n=i)] for i in range(12)]
    response, ctx = call(get_timeline(), phoenix=Phoenix(pages=pages))
    body = response.json()
    assert len(ctx.phoenix.span_requests()) == 10
    assert len(body["spans"]) == 10 and body["truncated"] is True


def test_ten_full_pages_and_no_more_is_not_truncated():
    pages = [[span(n=i)] for i in range(10)]
    response, _ = call(get_timeline(), phoenix=Phoenix(pages=pages))
    assert response.json()["truncated"] is False and len(response.json()["spans"]) == 10


def test_a_page_over_the_byte_cap_stops_the_read_and_is_marked_truncated(monkeypatch):
    big = [span(n=1, attributes={"input.value": "x" * 5000})]
    monkeypatch.setattr(phoenix_client, "MAX_PAGE_BYTES", 4096)
    response, ctx = call(get_timeline(), phoenix=Phoenix(pages=[[span(n=0)], big, [span(n=2)]]))
    body = response.json()
    assert response.status_code == 200
    assert body["truncated"] is True and body["note"] == talon_runs.PAGE_TOO_LARGE
    assert len(body["spans"]) == 1 and len(ctx.phoenix.span_requests()) == 2
    assert "xxxx" not in response.text


def test_a_cursor_that_does_not_move_is_a_502():
    def same(request, index):
        return httpx.Response(200, json={"data": [span(n=index)], "next_cursor": "c0" if index else "c0"})

    phoenix = Phoenix()
    phoenix.spans_answer = same
    response, ctx = call(get_timeline(), phoenix=phoenix)
    assert response.status_code == 502 and len(ctx.phoenix.span_requests()) == 2


# ── every span re-checked ─────────────────────────────────────────────────────


def test_spans_of_another_job_or_customer_are_dropped_and_counted():
    pages = [
        [
            span(n=0),
            span(job_id=JOB_GLOBEX, n=1),
            span(customer=GLOBEX, n=2),
            span(n=3, attributes={"job_id": None}),
            span(n=4, attributes={"customer_code": ACME.lower()}),
            {"name": "no attributes", "context": {"trace_id": "0" * 32, "span_id": "1" * 16}},
            "not a span",
            span(n=5, context={"trace_id": "not-hex", "span_id": "1" * 16}),
            span(n=6, start_time="yesterday"),
            span(n=7),
        ],
    ]
    response, _ = call(get_timeline(), phoenix=Phoenix(pages=pages))
    body = response.json()
    assert [s["trace_id"] for s in body["spans"]] == [f"{0:032x}", f"{7:032x}"]
    assert body["dropped"] == 8


def test_nothing_of_the_job_is_an_empty_timeline_with_a_note():
    response, _ = call(get_timeline(), phoenix=Phoenix(pages=[[span(job_id=JOB_GLOBEX)]]))
    body = response.json()
    assert body["spans"] == [] and body["dropped"] == 1 and body["note"] == "no trace data"


# ── the allowlist ─────────────────────────────────────────────────────────────


def planted_spans():
    """A span with the marker in every place the timeline must never read."""
    marker_attributes = {
        "input.value": MARKER,
        "input.mime_type": MARKER,
        "output.value": MARKER,
        "llm.input_messages.0.message.content": MARKER,
        "llm.input_messages.0.message.role": MARKER,
        "llm.output_messages.0.message.content": MARKER,
        "llm.invocation_parameters": MARKER,
        "llm.prompts": [MARKER],
        "gen_ai.input.messages": MARKER,
        "gen_ai.output.messages": MARKER,
        "gen_ai.system_instructions": MARKER,
        "final_result": MARKER,
        "pydantic_ai.all_messages": MARKER,
        "talon.scrubbed": True,
        "talon.scrub_replacements": MARKER,
        "tool_arguments": MARKER,
        "tool_response": MARKER,
        "exception.message": MARKER,
        "metadata": MARKER,
        "session.id": MARKER,
        "user.id": MARKER,
        "logfire.msg": f"invalid tool call: {MARKER}",
        "thread_id": MARKER,
    }
    events = [{"name": MARKER, "timestamp": "2026-10-16T08:00:01+00:00", "attributes": {"exception.message": MARKER}}]
    llm = span(n=0, status_message=MARKER, events=events, attributes=dict(marker_attributes))
    # A tool the model asked for that doesn't exist: Pydantic AI names the span after it.
    model_tool = span(
        n=1,
        name=f"execute_tool {MARKER}",
        span_kind="TOOL",
        status_code="ERROR",
        status_message=MARKER,
        attributes={**marker_attributes, "tool.name": MARKER, "gen_ai.tool.name": MARKER, "llm.model_name": None},
    )
    known_tool = span(
        n=2,
        name="execute_tool siem_search",
        span_kind="TOOL",
        attributes={"tool.name": "siem_search", "tool.parameters": MARKER},
    )
    agent = span(n=3, name="invoke_agent analyst-investigation", span_kind="AGENT", parent_id=None)
    odd = span(
        n=4,
        name=f"{MARKER} span",
        span_kind=MARKER,
        status_code=MARKER,
        parent_id=f"{3 + 1:016x}",
        attributes={
            "stage": MARKER,
            "role": f"Analyst {MARKER}",
            "llm.model_name": f"{MARKER} with spaces",
            "llm.token_count.prompt": MARKER,
        },
    )
    other_agent = span(n=5, name=f"invoke_agent {MARKER}", span_kind="AGENT")
    return [llm, model_tool, known_tool, agent, odd, other_agent]


def test_a_planted_marker_never_reaches_the_response_and_its_keys_are_the_allowlist():
    response, _ = call(get_timeline(), phoenix=Phoenix(pages=[planted_spans()]))
    assert response.status_code == 200
    assert MARKER.encode() not in response.content
    assert MARKER.lower().encode() not in response.content.lower()
    body = response.json()
    assert set(body) == TOP_KEYS
    assert len(body["spans"]) == 6 and body["dropped"] == 0
    for item in body["spans"]:
        assert set(item) == SPAN_KEYS
    llm, model_tool, known_tool, agent, odd, other_agent = body["spans"]
    assert (model_tool["name"], model_tool["tool"], model_tool["status_code"]) == ("TOOL span", None, "ERROR")
    assert (known_tool["name"], known_tool["tool"]) == ("execute_tool siem_search", "siem_search")
    assert known_tool["tool_label"] is None and model_tool["tool_label"] is None
    assert agent["name"] == "invoke_agent analyst-investigation" and agent["kind"] == "AGENT"
    assert (odd["name"], odd["kind"], odd["status_code"]) == ("UNKNOWN span", "UNKNOWN", "UNSET")
    assert (odd["stage"], odd["role"], odd["model"], odd["prompt_tokens"]) == (None, None, None, None)
    assert odd["parent_id"] == f"{4:016x}"
    assert other_agent["name"] == "AGENT span"


@pytest.mark.parametrize(
    "name, kind, shown",
    [
        ("chat claude-sonnet-5-5", "LLM", "chat claude-sonnet-5-5"),
        ("chat anthropic:claude-opus-5-5", "LLM", "chat anthropic:claude-opus-5-5"),
        ("model request attempt qwen3:32b", "LLM", "LLM span"),  # not one of the exact names
        ("chat qwen3:32b", "LLM", "chat qwen3:32b"),
        ("chat model@evil", "LLM", "LLM span"),
        ("chat " + "a" * 81, "LLM", "LLM span"),
        ("chat " + "a" * 80, "LLM", "chat " + "a" * 80),
        ("chat a model with spaces", "LLM", "LLM span"),
        ("invoke_agent reviewer", "AGENT", "invoke_agent reviewer"),
        ("invoke_agent analyst-template-chooser", "AGENT", "invoke_agent analyst-template-chooser"),
        ("invoke_agent someone-else", "AGENT", "AGENT span"),
        ("agent run", "AGENT", "agent run"),
        ("running tools", "CHAIN", "running tools"),
        ("execute_tool final_result", "TOOL", "execute_tool final_result"),
        ("execute_tool final_result_evil", "TOOL", "TOOL span"),
        ("execute_tool wazuh_agent_processes", "TOOL", "execute_tool wazuh_agent_processes"),
        ("execute_tool tavily_search", "TOOL", "execute_tool tavily_search"),
        ("execute_tool duckduckgo_search", "TOOL", "execute_tool duckduckgo_search"),  # older runs
        ("execute_tool ", "TOOL", "TOOL span"),
        ("anything else", "CHAIN", "CHAIN span"),
        (None, "UNKNOWN", "UNKNOWN span"),
        (["execute_tool", "siem_search"], "TOOL", "TOOL span"),
    ],
)
def test_only_known_span_names_are_shown(name, kind, shown):
    assert talon_runs.known_name(name, kind) == shown


@pytest.mark.parametrize(
    "tool, label",
    [("tavily_search", "Web search (Tavily)"), ("duckduckgo_search", "Web search (DuckDuckGo)"), ("siem_search", None)],
)
def test_web_search_tools_are_known_and_labelled(tool, label):
    item = talon_runs.to_dto(span(name=f"execute_tool {tool}", span_kind="TOOL", attributes={"tool.name": tool}))
    assert (item.name, item.tool, item.tool_label) == (f"execute_tool {tool}", tool, label)


def test_every_tool_label_is_a_known_tool():
    assert set(talon_runs.TOOL_LABELS) <= talon_runs.TOOL_NAMES


def test_token_counts_are_integers_only():
    item = talon_runs.to_dto(
        span(
            attributes={
                "llm.token_count.prompt": True,
                "llm.token_count.completion": -1,
                "llm.token_count.total": 12.0,
                "llm.token_count.prompt_details.cache_read": "100",
                "llm.token_count.prompt_details.cache_write": 7,
                "gen_ai.usage.input_tokens": 40,
            },
        ),
    )
    assert (item.prompt_tokens, item.completion_tokens, item.total_tokens, item.cache_read_tokens, item.cache_write_tokens) == (
        40,
        None,
        12,
        None,
        7,
    )


def test_unhashable_kinds_and_statuses_are_unknown_not_an_error():
    item = talon_runs.to_dto(span(span_kind=["LLM"], status_code={"code": "OK"}, attributes={"tool.name": ["siem_search"]}))
    assert (item.kind, item.status_code, item.tool) == ("UNKNOWN", "UNSET", None)


# ── the viewer key ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("role", ["MEMBER", "ADMIN", "SYSTEM", "viewer", None])
def test_a_key_that_isnt_a_viewers_reads_no_spans_and_is_a_502(role):
    response, ctx = call(get_timeline(), phoenix=Phoenix(role=role))
    assert (response.status_code, response.json()) == (502, {"detail": "Phoenix request failed"})
    assert ctx.phoenix.span_requests() == [] and len(ctx.phoenix.user_requests()) == 1


@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(401, json={"detail": "Not authenticated"}),
        httpx.Response(403, json={"detail": "Forbidden"}),
        httpx.Response(500, text="boom"),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"role": "VIEWER"}),  # not under data
        httpx.Response(200, json={"data": {"user_role": "VIEWER"}}),
        httpx.Response(200, json={"data": [{"role": "VIEWER"}]}),
        httpx.Response(302, headers={"location": "http://elsewhere.invalid/v1/user"}),
    ],
)
def test_anything_but_an_exact_viewer_answer_fails_closed(answer):
    phoenix = Phoenix()
    phoenix.user_answer = answer
    response, ctx = call(get_timeline(), phoenix=phoenix)
    assert response.status_code == 502 and ctx.phoenix.span_requests() == []
    assert [r.url.host for r in ctx.phoenix.requests] == ["phoenix-secret-host.invalid"]  # no redirect followed


def test_the_viewer_answer_is_cached_and_keyed_on_the_connector():
    async def scenario(client, ctx):
        await client.get(timeline(), headers=as_user("ana"))
        await client.get(timeline(), headers=as_user("ana"))
        first = len(ctx.phoenix.user_requests())
        ctx.phoenix_attributes.return_value = phoenix_connector(connector_last_updated=datetime(2026, 10, 16, 9, 0))
        ctx.phoenix.role = "MEMBER"
        changed = await client.get(timeline(), headers=as_user("ana"))
        return first, len(ctx.phoenix.user_requests()), changed.status_code

    assert call(scenario) == (1, 2, 502)


def test_a_new_key_is_checked_again_even_with_the_same_timestamp():
    async def scenario(client, ctx):
        await client.get(timeline(), headers=as_user("ana"))
        ctx.phoenix_attributes.return_value = phoenix_connector(connector_api_key="another-key")
        await client.get(timeline(), headers=as_user("ana"))
        return len(ctx.phoenix.user_requests())

    assert call(scenario) == 2


def test_a_failed_role_check_is_not_cached():
    async def scenario(client, ctx):
        ctx.phoenix.user_answer = httpx.Response(503, text="starting")
        first = await client.get(timeline(), headers=as_user("ana"))
        ctx.phoenix.user_answer = None
        second = await client.get(timeline(), headers=as_user("ana"))
        return first.status_code, second.status_code

    assert call(scenario) == (502, 200)


@pytest.mark.parametrize("connector", [None, phoenix_connector(connector_api_key=""), phoenix_connector(connector_url="  ")])
def test_an_unconfigured_connector_is_a_502_with_no_phoenix_request(connector):
    response, ctx = call(get_timeline(), connector=connector)
    assert (response.status_code, response.json()) == (502, {"detail": "Phoenix request failed"})
    assert ctx.phoenix.requests == []


# ── every Phoenix request is a GET ────────────────────────────────────────────


def test_the_phoenix_client_refuses_to_send_anything_but_get():
    seen = []

    def handler(request):
        seen.append(request.method)
        return httpx.Response(200, json={})

    async def scenario():
        phoenix_client._transport, original = (lambda: httpx.MockTransport(handler)), phoenix_client._transport
        try:
            async with phoenix_client._new_client() as client:
                for method in ("POST", "PUT", "PATCH", "DELETE"):
                    with pytest.raises(phoenix_client.NotGet):
                        await client.request(method, f"{PHOENIX_URL}/v1/projects")
                await client.get(f"{PHOENIX_URL}/v1/user")
        finally:
            phoenix_client._transport = original

    asyncio.run(scenario())
    assert seen == ["GET"]


def test_the_phoenix_client_trusts_no_proxy_and_follows_no_redirect():
    async def scenario():
        async with phoenix_client._new_client() as client:
            return client.trust_env, client.follow_redirects, client.timeout

    trust_env, follow, timeout = asyncio.run(scenario())
    assert trust_env is False and follow is False
    assert (timeout.connect, timeout.read) == (5.0, 20.0)


def test_a_run_view_sends_phoenix_gets_only():
    pages = [[span(n=i)] for i in range(3)]
    _, ctx = call(get_timeline(), phoenix=Phoenix(pages=pages))
    assert ctx.phoenix.requests and {r.method for r in ctx.phoenix.requests} == {"GET"}


# ── Phoenix's answers ─────────────────────────────────────────────────────────


def test_no_project_yet_is_an_empty_timeline_with_a_note_and_phoenix_text_isnt_relayed():
    response, ctx = call(get_timeline(), phoenix=Phoenix(projects=()))
    assert response.status_code == 200
    assert response.json() == {
        "job_id": JOB_ACME,
        "customer_code": ACME,
        "spans": [],
        "truncated": False,
        "dropped": 0,
        "note": "no trace data",
    }
    assert "Project with name" not in response.text


@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(401, json={"detail": "Phoenix says: invalid key PHX-TEXT"}),
        httpx.Response(403, json={"detail": "PHX-TEXT forbidden"}),
        httpx.Response(422, json={"detail": "Invalid attribute 'PHX-TEXT'"}),
        httpx.Response(500, text="Traceback PHX-TEXT"),
        httpx.Response(503, text="PHX-TEXT"),
        httpx.Response(200, text="PHX-TEXT not json"),
        httpx.Response(200, json={"spans": ["PHX-TEXT"]}),
        httpx.Response(200, json={"data": [], "next_cursor": 5}),
        httpx.Response(307, headers={"location": "http://elsewhere.invalid/PHX-TEXT"}),
    ],
)
def test_any_other_phoenix_answer_is_a_502_with_the_fixed_text(answer):
    phoenix = Phoenix()
    phoenix.spans_answer = lambda request, index: answer
    response, ctx = call(get_timeline(), phoenix=phoenix)
    assert (response.status_code, response.json()) == (502, {"detail": "Phoenix request failed"})
    assert "PHX-TEXT" not in response.text and response.headers["cache-control"] == "no-store"


def test_a_404_after_the_first_page_is_a_502():
    phoenix = Phoenix(pages=[[span(n=0)], [span(n=1)]])
    first = phoenix.handler

    async def handler(request):
        if request.url.params.get("cursor"):
            phoenix.requests.append(request)
            return httpx.Response(404, json={"detail": "gone"})
        return await first(request)

    phoenix.handler = handler
    response, _ = call(get_timeline(), phoenix=phoenix)
    assert response.status_code == 502


def test_a_transport_error_is_a_502_and_neither_the_key_nor_the_url_is_logged():
    lines = []
    sink = logger.add(lambda message: lines.append(str(message)), level="DEBUG")
    try:
        phoenix = Phoenix()

        def unreachable(request, index):
            raise httpx.ConnectError(f"connection to {PHOENIX_URL} refused; Authorization: Bearer {PHOENIX_KEY}")

        phoenix.spans_answer = unreachable
        failed, _ = call(get_timeline(), phoenix=phoenix)
        refused = Phoenix(role="MEMBER")
        not_viewer, _ = call(get_timeline(), phoenix=refused)
        ok, _ = call(get_timeline())
    finally:
        logger.remove(sink)
    assert failed.status_code == 502 and not_viewer.status_code == 502 and ok.status_code == 200
    logged = "\n".join(lines)
    assert lines and PHOENIX_KEY not in logged and "phoenix-secret-host" not in logged
    assert PHOENIX_KEY not in failed.text and "phoenix-secret-host" not in failed.text


def test_two_reads_at_once_and_a_third_waits_then_is_busy(monkeypatch):
    monkeypatch.setattr(phoenix_client, "QUEUE_WAIT", 0.2)
    phoenix = Phoenix()

    async def scenario(client, ctx):
        ctx.phoenix.gate = asyncio.Event()
        first = asyncio.create_task(client.get(timeline(), headers=as_user("ana")))
        second = asyncio.create_task(client.get(timeline(), headers=as_user("admin")))
        while len(ctx.phoenix.span_requests()) < 2:
            await asyncio.sleep(0.01)
        third = await client.get(timeline(), headers=as_user("resp"))
        ctx.phoenix.gate.set()
        return third, await first, await second, len(ctx.phoenix.span_requests())

    third, first, second, reads = call(scenario, phoenix=phoenix)
    assert (third.status_code, third.json()) == (503, {"detail": "Phoenix reads are busy; try again shortly"})
    assert third.headers["cache-control"] == "no-store"
    assert first.status_code == second.status_code == 200 and reads == 2


def test_a_slot_is_given_back_after_a_failure():
    async def scenario(client, ctx):
        ctx.phoenix.spans_answer = lambda request, index: httpx.Response(500)
        statuses = [(await client.get(timeline(), headers=as_user("ana"))).status_code for _ in range(3)]
        ctx.phoenix.spans_answer = None
        statuses.append((await client.get(timeline(), headers=as_user("ana"))).status_code)
        return statuses

    assert call(scenario) == [502, 502, 502, 200]


# ── the connector ─────────────────────────────────────────────────────────────


def test_the_talon_phoenix_connector_is_seeded_from_its_env_vars(monkeypatch):
    monkeypatch.setenv("TALON_PHOENIX_URL", "http://talon-analyst-phoenix:6006")
    monkeypatch.setenv("TALON_PHOENIX_API_KEY", "seeded-key")
    (row,) = [c for c in db_populate.get_connectors_list() if c["connector_name"] == "Talon Phoenix"]
    assert (row["connector_type"], row["connector_accepts_api_key"]) == ("20.20", True)
    assert (row["connector_url"], row["connector_api_key"]) == ("http://talon-analyst-phoenix:6006", "seeded-key")
    assert "VIEWER" in row["connector_description"]
    assert get_connector_service("Talon Phoenix") is TalonPhoenixService


def verify(attributes, phoenix):
    async def scenario():
        phoenix_client._transport, original = (lambda: httpx.MockTransport(phoenix.handler)), phoenix_client._transport
        try:
            return await phoenix_client.verify_talon_phoenix_credentials(attributes)
        finally:
            phoenix_client._transport = original

    return asyncio.run(scenario())


@pytest.mark.parametrize(
    "role, user_answer, passes",
    [
        ("VIEWER", None, True),
        ("MEMBER", None, False),
        ("ADMIN", None, False),
        (None, None, False),  # authentication off: an anonymous user
        ("VIEWER", httpx.Response(401, json={"detail": "Not authenticated"}), False),
        ("VIEWER", httpx.Response(500, text="boom"), False),
        ("VIEWER", httpx.Response(200, json={"data": {"role": "VIEWER "}}), False),
    ],
)
def test_the_connector_check_passes_only_for_a_viewer_and_never_echoes_the_url_or_key(role, user_answer, passes):
    phoenix = Phoenix(role=role)
    phoenix.user_answer = user_answer
    result = verify(phoenix_connector(), phoenix)
    assert result["connectionSuccessful"] is passes
    assert PHOENIX_KEY not in result["message"] and "phoenix-secret-host" not in result["message"]
    assert [r.method for r in phoenix.requests] == ["GET"] and phoenix.requests[0].url.path == "/v1/user"
    assert phoenix.requests[0].headers["authorization"] == f"Bearer {PHOENIX_KEY}"


def test_the_connector_check_without_a_key_or_unreachable_fails_without_echoing():
    phoenix = Phoenix()
    assert verify(phoenix_connector(connector_api_key=""), phoenix)["connectionSuccessful"] is False
    assert phoenix.requests == []

    def unreachable(request):
        raise httpx.ConnectError(f"{PHOENIX_URL} refused")

    async def scenario():
        phoenix_client._transport, original = (lambda: httpx.MockTransport(unreachable)), phoenix_client._transport
        try:
            return await phoenix_client.verify_talon_phoenix_credentials(phoenix_connector())
        finally:
            phoenix_client._transport = original

    result = asyncio.run(scenario())
    assert result == {"connectionSuccessful": False, "message": "Phoenix could not be reached"}


def test_the_project_rule_is_one_constant():
    # talon-analyst ``config._CUSTOMER_CODE`` with ``CUSTOMER_CODE_MAX`` (64), as ``project_for`` uses it.
    assert talon_runs.PROJECT_CUSTOMER.pattern == r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}"
    assert CHAT == "chat" and talon_runs.project_for(CHAT) is None


# ── review of #1271: hostile Phoenix answers ──────────────────────────────────


def test_a_stacked_gzip_page_is_refused_without_being_inflated():
    phoenix = Phoenix()
    stacked_gzip()  # made before measuring: the test's own 64 MB isn't the client's
    phoenix.spans_answer = lambda request, index: bomb_response()
    tracemalloc.start()
    try:
        response, ctx = call(get_timeline(), phoenix=phoenix)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert (response.status_code, response.json()) == (502, {"detail": "Phoenix request failed"})
    assert peak < 16 * 1024 * 1024  # 64 MB once inflated; refused raw, it never is


@pytest.mark.parametrize("encoding", ["gzip", "deflate", "br", "gzip, identity", "identity, gzip", "x-custom"])
def test_any_content_encoding_but_identity_is_refused(encoding):
    phoenix = Phoenix()
    phoenix.spans_answer = lambda request, index: httpx.Response(
        200,
        headers={"content-encoding": encoding},
        stream=RawStream(json.dumps({"data": [span()], "next_cursor": None}).encode()),
    )
    response, _ = call(get_timeline(), phoenix=phoenix)
    assert response.status_code == 502


@pytest.mark.parametrize("encoding", ["identity", "Identity", " identity "])
def test_an_identity_encoding_is_read(encoding):
    phoenix = Phoenix()
    phoenix.spans_answer = lambda request, index: httpx.Response(
        200,
        headers={"content-encoding": encoding},
        stream=RawStream(json.dumps({"data": [span()], "next_cursor": None}).encode()),
    )
    response, _ = call(get_timeline(), phoenix=phoenix)
    assert response.status_code == 200 and len(response.json()["spans"]) == 1


def test_a_stacked_gzip_user_answer_is_no_role():
    phoenix = Phoenix()
    phoenix.user_answer = bomb_response()
    response, ctx = call(get_timeline(), phoenix=phoenix)
    assert response.status_code == 502 and ctx.phoenix.span_requests() == []
    assert verify(phoenix_connector(), phoenix)["connectionSuccessful"] is False


def test_every_phoenix_request_asks_for_identity():
    _, ctx = call(get_timeline())
    assert {r.headers["accept-encoding"] for r in ctx.phoenix.requests} == {"identity"}


def test_at_most_page_size_spans_are_taken_from_a_page():
    page = [span(n=i) for i in range(talon_runs.PAGE_SIZE * 50)]  # 5000 where 100 were asked for
    response, ctx = call(get_timeline(), phoenix=Phoenix(pages=[page, [span(n=99999)]]))
    body = response.json()
    assert len(body["spans"]) == talon_runs.PAGE_SIZE and body["truncated"] is True
    assert len(ctx.phoenix.span_requests()) == 1


def test_a_timeline_holds_at_most_max_spans():
    pages = [[span(n=p * 100 + i) for i in range(100)] for p in range(12)]
    response, ctx = call(get_timeline(), phoenix=Phoenix(pages=pages))
    body = response.json()
    assert len(body["spans"]) == talon_runs.MAX_SPANS == 1000 and body["truncated"] is True
    assert len(ctx.phoenix.span_requests()) == 10


def test_the_span_cap_stops_paging(monkeypatch):
    monkeypatch.setattr(talon_runs, "MAX_SPANS", 5)
    pages = [[span(n=p * 3 + i) for i in range(3)] for p in range(4)]
    response, ctx = call(get_timeline(), phoenix=Phoenix(pages=pages))
    body = response.json()
    assert len(body["spans"]) == 5 and body["truncated"] is True and len(ctx.phoenix.span_requests()) == 2


def test_exactly_the_cap_with_nothing_more_is_not_truncated(monkeypatch):
    monkeypatch.setattr(talon_runs, "MAX_SPANS", 4)
    response, _ = call(get_timeline(), phoenix=Phoenix(pages=[[span(n=0), span(n=1)], [span(n=2), span(n=3)]]))
    assert len(response.json()["spans"]) == 4 and response.json()["truncated"] is False


def test_a_repeated_span_is_shown_once():
    pages = [[span(n=0), span(n=0), span(n=1)], [span(n=1), span(n=2)]]
    response, _ = call(get_timeline(), phoenix=Phoenix(pages=pages))
    body = response.json()
    assert [s["span_id"] for s in body["spans"]] == [f"{1:016x}", f"{2:016x}", f"{3:016x}"]
    assert body["dropped"] == 2


def dribble():
    return httpx.Response(200, stream=RawStream(b" ", chunk=1, delay=0.05, forever=True))


def test_a_dribbling_phoenix_hits_the_timelines_deadline_and_gives_the_slot_back(monkeypatch):
    monkeypatch.setattr(talon_runs, "TIMELINE_DEADLINE_SECONDS", 0.3)
    monkeypatch.setattr(phoenix_client, "QUEUE_WAIT", 0.2)

    async def scenario(client, ctx):
        ctx.phoenix.spans_answer = lambda request, index: dribble()
        started = time.monotonic()
        slow = [(await client.get(timeline(), headers=as_user("ana"))).status_code for _ in range(3)]
        elapsed = time.monotonic() - started
        ctx.phoenix.spans_answer = None
        after = await client.get(timeline(), headers=as_user("ana"))
        return slow, elapsed, after.status_code

    slow, elapsed, after = call(scenario)
    assert slow == [502, 502, 502] and elapsed < 5 and after == 200  # three over two slots: none leaked


def test_each_request_has_its_own_total_deadline(monkeypatch):
    monkeypatch.setattr(phoenix_client, "USER_TOTAL_SECONDS", 0.2)

    async def scenario(client, ctx):
        ctx.phoenix.user_answer = dribble()
        first = await client.get(timeline(), headers=as_user("ana"))
        ctx.phoenix.user_answer = None
        second = await client.get(timeline(), headers=as_user("ana"))
        return first.status_code, second.status_code, len(ctx.phoenix.user_requests())

    assert call(scenario) == (502, 200, 2)  # the timed-out check isn't cached


def test_a_page_read_has_its_own_total_deadline(monkeypatch):
    monkeypatch.setattr(phoenix_client, "GET_TOTAL_SECONDS", 0.2)
    phoenix = Phoenix()
    phoenix.spans_answer = lambda request, index: dribble()
    started = time.monotonic()
    response, _ = call(get_timeline(), phoenix=phoenix)
    assert response.status_code == 502 and time.monotonic() - started < 5


def test_deeply_nested_json_is_a_502_not_a_500():
    phoenix = Phoenix()
    phoenix.spans_answer = lambda request, index: httpx.Response(200, content=deeply_nested())
    response, _ = call(get_timeline(), phoenix=phoenix)
    assert (response.status_code, response.json()) == (502, {"detail": "Phoenix request failed"})


def test_a_deeply_nested_user_answer_is_no_role():
    phoenix = Phoenix()
    phoenix.user_answer = httpx.Response(200, content=b'{"data": ' + b"[" * 50_000 + b"]" * 50_000 + b"}")
    response, ctx = call(get_timeline(), phoenix=phoenix)
    assert response.status_code == 502 and ctx.phoenix.span_requests() == []


@pytest.mark.parametrize(
    "field, value",
    [
        ("role", MARKER),
        ("role", "admin"),
        ("role", "analyst "),
        ("stage", MARKER),
        ("stage", f"S5-{MARKER.lower()}"),
        ("stage", "S11"),
        ("stage", "s5"),
        ("llm.model_name", f"{MARKER}@host"),
        ("llm.model_name", "m" * 81),
        ("llm.model_name", f"claude {MARKER}"),
    ],
)
def test_free_text_in_role_stage_and_model_is_null(field, value):
    extra = {"name": f"chat {value}"} if field == "llm.model_name" else {}
    planted = span(attributes={field: value, "gen_ai.response.model": None}, **extra)
    response, _ = call(get_timeline(), phoenix=Phoenix(pages=[[planted]]))
    (item,) = response.json()["spans"]
    key = {"llm.model_name": "model"}.get(field, field)
    assert item[key] is None
    assert MARKER.encode() not in response.content
    if field == "llm.model_name":
        assert item["name"] == "LLM span"


@pytest.mark.parametrize("stage", ["S0", "S4", "S5", "S5-escalation", "S5-revision", "S6", "S10", "chat", "chat-memory"])
def test_talon_analysts_own_stages_are_shown(stage):
    item = talon_runs.to_dto(span(attributes={"stage": stage}))
    assert item.stage == stage


@pytest.mark.parametrize("role", ["analyst", "analyst-chat-memory"])
def test_talon_analysts_own_roles_are_shown(role):
    assert talon_runs.to_dto(span(attributes={"role": role})).role == role


def test_a_running_jobs_window_is_capped_a_day_after_it_began():
    job = talon_runs.JobFacts(job_id=JOB_RUNNING, customer_code=ACME, created_at=CREATED, completed_at=None)
    start, end = talon_runs.time_window(job, now=CREATED + timedelta(days=3))
    assert (start, end) == ("2026-10-16T07:58:00Z", "2026-10-17T08:15:00Z")
