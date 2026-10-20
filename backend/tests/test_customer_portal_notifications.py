"""Customer Portal user notifications (#1282): the rules, with no database.

What reaches whom (preferences, severity threshold, the actor, a report's requester),
when a digest is due, what the emails say when no template is set or one is broken,
the built-in templates, the request shapes, the routes' scopes, and the hooks in the
incident and report code.

``tests/e2e/customer_portal_notifications_e2e.py`` runs it all on MySQL.

Run with: cd backend && python -m pytest tests/test_customer_portal_notifications.py
"""

import asyncio
import inspect
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi.routing import APIRoute  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.customer_portal.schema.notifications import (  # noqa: E402
    MarkPortalNotificationsReadRequest,
)
from app.customer_portal.schema.notifications import (  # noqa: E402
    NotificationPreference,
)
from app.customer_portal.schema.notifications import (  # noqa: E402
    UpdatePortalNotificationPreferencesRequest,
)
from app.customer_portal.services import notification_email as email  # noqa: E402
from app.customer_portal.services import notification_events as events  # noqa: E402
from app.customer_portal.services import notifications as service  # noqa: E402
from app.db.universal_models import CustomerPortalNotification  # noqa: E402
from app.db.universal_models import CustomerPortalNotificationPref  # noqa: E402
from app.notifications.schema.notifications import DISPATCH_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import PORTAL_TRIGGERS  # noqa: E402
from app.notifications.schema.notifications import NotificationRouteCreate  # noqa: E402
from app.notifications.schema.notifications import NotificationTrigger  # noqa: E402
from app.notifications.services.template_seeds import PORTAL_TEMPLATES  # noqa: E402

CC = "ACME"


def _event(**fields) -> service.PortalEvent:
    base = dict(
        event=service.EVENT_ALERT_CREATED,
        customer_code=CC,
        entity_type="alert",
        entity_id=7,
        dedupe_key="alert_created:alert:7",
        title="New High alert: x",
        severity="High",
    )
    return service.PortalEvent(**{**base, **fields})


def _user(user_id=1, email_address="jane@acme.example", username="jane"):
    return SimpleNamespace(id=user_id, email=email_address, username=username)


def _row(**fields) -> CustomerPortalNotification:
    base = dict(
        id=1,
        user_id=1,
        customer_code=CC,
        event="alert_created",
        entity_type="alert",
        entity_id=7,
        dedupe_key="k",
        title="New High alert: Suspicious login",
        body="A login from an unusual country.",
        severity="High",
        created_at=datetime(2026, 10, 1, 8, 15),
    )
    return CustomerPortalNotification(**{**base, **fields})


# ── Preferences ───────────────────────────────────────────────────────────────


class TestPreferences:
    def test_defaults_are_the_bell_only_and_alerts_from_high(self):
        prefs = service.effective_preferences([])
        assert list(prefs) == list(service.EVENTS)
        for pref in prefs.values():
            assert (pref.in_app, pref.email) == (True, "off")
        assert prefs["alert_created"].threshold == "High"
        assert prefs["case_closed"].min_severity is None

    def test_stored_choices_win_and_unknown_values_read_as_defaults(self):
        rows = [
            CustomerPortalNotificationPref(user_id=1, event="alert_created", in_app=False, email="digest", min_severity="critical"),
            CustomerPortalNotificationPref(user_id=1, event="case_closed", in_app=True, email="carrier-pigeon"),
            CustomerPortalNotificationPref(user_id=1, event="retired_event", in_app=False, email="immediate"),
        ]
        prefs = service.effective_preferences(rows)
        assert (prefs["alert_created"].in_app, prefs["alert_created"].email, prefs["alert_created"].threshold) == (
            False,
            "digest",
            "Critical",
        )
        assert prefs["case_closed"].email == "off"
        assert "retired_event" not in prefs


# ── Who gets what ─────────────────────────────────────────────────────────────


class TestDelivery:
    @pytest.mark.parametrize(
        "severity,threshold,expected",
        [
            ("Critical", "High", True),
            ("High", "High", True),
            ("Medium", "High", False),
            ("Low", "Low", True),
            ("Informational", "Low", False),
        ],
    )
    def test_new_alerts_from_the_users_threshold_up(self, severity, threshold, expected):
        pref = service.Preference(event="alert_created", min_severity=threshold)
        assert (service.delivery_for(pref, _event(severity=severity)) is not None) is expected

    def test_an_alert_without_a_known_severity_is_below_every_threshold_but_its_default(self):
        # Callers pass severity_of(alert), which never returns None; a junk value ranks lowest.
        pref = service.Preference(event="alert_created", min_severity="Informational")
        assert service.delivery_for(pref, _event(severity="bogus")) is None

    def test_the_threshold_applies_to_new_alerts_only(self):
        pref = service.Preference(event="case_closed", min_severity="Critical")
        assert service.delivery_for(pref, _event(event="case_closed", severity=None)) is not None

    @pytest.mark.parametrize(
        "in_app,email_mode,expected",
        [
            (True, "off", service.Delivery(in_app=True, email_mode="none")),
            (True, "immediate", service.Delivery(in_app=True, email_mode="immediate")),
            (False, "digest", service.Delivery(in_app=False, email_mode="digest")),
            (False, "off", None),
        ],
    )
    def test_bell_and_email_as_chosen(self, in_app, email_mode, expected):
        pref = service.Preference(event="report_ready", in_app=in_app, email=email_mode)
        assert service.delivery_for(pref, _event(event="report_ready", severity=None)) == expected

    def test_the_actor_is_never_told_and_a_narrowed_event_reaches_only_its_users(self):
        assert service.wants(5, _event(actor_user_id=5)) is False
        assert service.wants(6, _event(actor_user_id=5)) is True
        assert service.wants(6, _event(only_user_ids=frozenset({5}))) is False
        assert service.wants(5, _event(only_user_ids=frozenset({5}))) is True

    def test_an_email_that_cannot_go_out_says_why(self):
        with patch.object(service, "email_configured", return_value=False):
            assert service.email_problem(_user()) == "SMTP is not configured"
        with patch.object(service, "email_configured", return_value=True):
            assert service.email_problem(_user(email_address="")) == "The user has no email address"
            assert service.email_problem(_user()) is None

    def test_the_row_records_a_skipped_email_and_keeps_the_bell(self):
        delivery = service.Delivery(in_app=True, email_mode="immediate")
        with patch.object(service, "email_configured", return_value=False):
            row = service.new_row(_user(), _event(), delivery)
        assert (row.in_app, row.email_mode, row.email_status, row.email_error) == (True, "immediate", "skipped", "SMTP is not configured")
        with patch.object(service, "email_configured", return_value=True):
            row = service.new_row(_user(), _event(title="x" * 300, dedupe_key="k" * 300), delivery)
        assert (row.email_status, len(row.title), len(row.dedupe_key)) == ("pending", 255, 191)

    def test_a_bell_only_row_has_no_email_state(self):
        row = service.new_row(_user(), _event(), service.Delivery(in_app=True, email_mode="none"))
        assert (row.email_mode, row.email_status) == ("none", None)


# ── The digest ────────────────────────────────────────────────────────────────


class TestDigest:
    @pytest.mark.parametrize(
        "now,last_sent,due",
        [
            (datetime(2026, 10, 2, 6, 59), None, False),  # before today's hour
            (datetime(2026, 10, 2, 7, 0), None, True),
            (datetime(2026, 10, 2, 7, 0), datetime(2026, 10, 1, 7, 5), True),  # yesterday's
            (datetime(2026, 10, 2, 7, 30), datetime(2026, 10, 2, 7, 15), False),  # already today
            (datetime(2026, 10, 2, 22, 0), datetime(2026, 10, 1, 7, 0), True),  # a run that missed the hour
        ],
    )
    def test_once_a_day_from_the_digest_hour(self, now, last_sent, due):
        assert service.digest_due(now, last_sent, 7) is due

    @pytest.mark.parametrize("raw,hour", [(None, 7), ("", 7), ("0", 0), ("23", 23), ("24", 7), ("-1", 7), ("seven", 7)])
    def test_the_hour_comes_from_the_environment(self, raw, hour, monkeypatch):
        if raw is None:
            monkeypatch.delenv("PORTAL_NOTIFICATION_DIGEST_HOUR", raising=False)
        else:
            monkeypatch.setenv("PORTAL_NOTIFICATION_DIGEST_HOUR", raw)
        assert service.digest_hour() == hour


# ── Request shapes ────────────────────────────────────────────────────────────


class TestSchemas:
    def test_a_severity_only_for_new_alerts(self):
        NotificationPreference(event="alert_created", min_severity="Medium")
        with pytest.raises(ValidationError, match="alert_created only"):
            NotificationPreference(event="case_closed", min_severity="Medium")

    @pytest.mark.parametrize(
        "body",
        [
            {"event": "nope"},
            {"event": "case_closed", "email": "weekly"},
            {"event": "alert_created", "min_severity": "Severe"},
            {"event": "case_closed", "user_id": 2},
        ],
    )
    def test_refuses_what_it_does_not_know(self, body):
        with pytest.raises(ValidationError):
            NotificationPreference(**body)

    def test_each_event_once_and_at_least_one(self):
        with pytest.raises(ValidationError, match="once"):
            UpdatePortalNotificationPreferencesRequest(preferences=[{"event": "case_closed"}, {"event": "case_closed"}])
        with pytest.raises(ValidationError):
            UpdatePortalNotificationPreferencesRequest(preferences=[])

    def test_mark_read_takes_ids_or_all(self):
        MarkPortalNotificationsReadRequest(ids=[1, 2])
        MarkPortalNotificationsReadRequest(all=True)
        for body in ({}, {"ids": [1], "all": True}):
            with pytest.raises(ValidationError, match="either ids or all"):
                MarkPortalNotificationsReadRequest(**body)
        with pytest.raises(ValidationError):
            MarkPortalNotificationsReadRequest(ids=list(range(201)))


# ── Emails ────────────────────────────────────────────────────────────────────


class TestEmails:
    def test_links_need_the_portal_url(self, monkeypatch):
        monkeypatch.delenv("CUSTOMER_PORTAL_URL", raising=False)
        assert email.item_url("alert", 7) == ""
        monkeypatch.setenv("CUSTOMER_PORTAL_URL", "https://portal.example.com/")
        assert email.item_url("alert", 7) == "https://portal.example.com/alerts/7"
        assert email.item_url("case", 3) == "https://portal.example.com/cases/3"
        assert email.item_url("report", 9) == "https://portal.example.com/reports"

    def test_the_plaintext_for_one_notification(self, monkeypatch):
        monkeypatch.setenv("CUSTOMER_PORTAL_URL", "https://portal.example.com")
        text = email.plaintext(_user(), "Acme Corp", [_row()])
        assert "Hello jane," in text
        assert "New High alert: Suspicious login" in text and "A login from an unusual country." in text
        assert "https://portal.example.com/alerts/7" in text
        assert "https://portal.example.com/profile?tab=notifications" in text  # where to change it

    def test_the_plaintext_digest_groups_by_event(self, monkeypatch):
        monkeypatch.delenv("CUSTOMER_PORTAL_URL", raising=False)
        rows = [_row(), _row(id=2, event="case_closed", entity_type="case", entity_id=3, title="Case closed: Phishing")]
        text = email.plaintext(_user(), "Acme Corp", rows)
        assert text.index("New alerts") < text.index("Closed cases")
        assert "- Case closed: Phishing" in text and "http" not in text
        assert "Profile → Notifications" in text  # no URL: named instead

    def test_no_template_sends_the_plaintext(self):
        subject, text, html = asyncio.run(
            email.render_with(MagicMock(), template=None, event=MagicMock(), extra={}, fallback=("Subject", "Body")),
        )
        assert (subject, text, html) == ("Subject", "Body", None)

    def test_a_broken_template_never_costs_the_email(self):
        template = SimpleNamespace(id=1, name="Broken", format="html", body_template="{{ nope(", subject_template=None)
        event = email.build_event(
            NotificationTrigger.PORTAL_CASE_CLOSED,
            customer_code=CC,
            title="Case closed: x",
            body=None,
            severity=None,
            entity_type="case",
            entity_id=3,
            link="",
        )
        subject, text, html = asyncio.run(email.render_with(MagicMock(), template=template, event=event, extra={}, fallback=("S", "B")))
        assert (subject, text, html) == ("S", "B", None)

    def test_an_html_template_gets_a_text_part_and_a_one_line_subject(self):
        template = SimpleNamespace(
            id=1,
            name="Ok",
            format="html",
            body_template="<p>Hello {{ user_name }}</p><p>{{ subject }}</p>",
            subject_template="{{ subject }}\nBcc: evil@example.com",
        )
        event = email.build_event(
            NotificationTrigger.PORTAL_CASE_CLOSED,
            customer_code=CC,
            title="Case closed: <x>",
            body=None,
            severity=None,
            entity_type="case",
            entity_id=3,
            link="",
        )
        extra = email.build_extra_context(user_name="jane", customer_code=CC, customer_name="Acme", event="case_closed")
        subject, text, html = asyncio.run(email.render_with(MagicMock(), template=template, event=event, extra=extra, fallback=("S", "B")))
        assert "\n" not in subject and subject.startswith("Case closed: &lt;x&gt;")
        assert "&lt;x&gt;" in html and "Hello jane" in text and "<p>" not in text

    def test_a_template_is_the_customers_then_shared_then_built_in_never_another_customers(self):
        def tpl(name, customer_code=None, is_default=False):
            return SimpleNamespace(name=name, customer_code=customer_code, is_default=is_default)

        rows = [tpl("built-in", is_default=True), tpl("other", customer_code="OTHER"), tpl("shared"), tpl("mine", customer_code=CC)]
        session = MagicMock()
        session.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: rows)))
        assert asyncio.run(email.resolve_template(session, NotificationTrigger.PORTAL_CASE_CLOSED, CC)).name == "mine"
        assert asyncio.run(email.resolve_template(session, NotificationTrigger.PORTAL_CASE_CLOSED, "THIRD")).name == "shared"
        session.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: rows[:2])))
        assert asyncio.run(email.resolve_template(session, NotificationTrigger.PORTAL_CASE_CLOSED, "THIRD")).name == "built-in"


class TestTemplates:
    def test_portal_triggers_are_template_scopes_never_route_triggers(self):
        assert PORTAL_TRIGGERS.isdisjoint(DISPATCH_TRIGGERS)
        with pytest.raises(ValidationError, match="not a route trigger"):
            NotificationRouteCreate(trigger="portal_case_closed", channel="webhook", config={"url": "https://example.com"})

    def test_one_built_in_per_portal_trigger(self):
        assert sorted(t["trigger"] for t in PORTAL_TEMPLATES) == sorted(t.value for t in PORTAL_TRIGGERS)
        assert all(t["format"] == "html" for t in PORTAL_TEMPLATES)

    @pytest.mark.parametrize("spec", PORTAL_TEMPLATES, ids=lambda spec: spec["trigger"])
    def test_every_built_in_previews_without_error(self, spec):
        from app.notifications.services import templates

        payload = SimpleNamespace(
            format="html",
            trigger=spec["trigger"],
            customer_code=None,
            body_template=spec["body_template"],
            subject_template=spec["subject_template"],
        )
        branding = {"logo": None, "title": "Acme", "accent": "#123456", "accent_strong": "#123456", "accent_text": "#fff"}
        with patch.object(templates, "build_branding_context", AsyncMock(return_value=branding)), patch.object(
            email,
            "customer_name_for",
            AsyncMock(return_value="Acme Corp"),
        ):
            out = asyncio.run(templates.preview(payload, MagicMock()))
        assert out["error"] is None
        assert out["subject"]
        assert "Hello jdoe" in out["body"] and "Acme Corp" in out["body"]

    def test_the_built_in_digest_lists_every_item(self):
        from app.notifications.services.rendering import render

        spec = next(t for t in PORTAL_TEMPLATES if t["trigger"] == "portal_digest")
        rows = [_row(id=i, title=f"Item {i}") for i in range(3)]
        extra = email.build_extra_context(
            user_name="jane",
            customer_code=CC,
            customer_name="Acme",
            items=[email.item_view(row) for row in rows],
        )
        from app.notifications.services.templates import _FALLBACK_BRANDING

        extra["branding"] = dict(_FALLBACK_BRANDING)  # what build_branding_context gives at worst
        event = email.build_event(
            NotificationTrigger.PORTAL_DIGEST,
            customer_code=CC,
            title="t",
            body=None,
            severity=None,
            entity_type="user",
            entity_id=1,
            link="",
        )
        html = render(spec["body_template"], event, autoescape=True, extra_context=extra)
        assert all(f"Item {i}" in html for i in range(3))
        assert render(spec["subject_template"], event, autoescape=True, extra_context=extra) == "Your daily summary: 3 notifications"


# ── Events ────────────────────────────────────────────────────────────────────


def _session_with(objects, scalar=None):
    session = MagicMock()

    async def get(model, key):
        return objects.get((model.__name__, key))

    session.get = get
    session.execute = AsyncMock(return_value=SimpleNamespace(scalar=lambda: scalar))
    return session


class TestEvents:
    def test_a_report_a_portal_user_asked_for_is_theirs_alone(self):
        report = SimpleNamespace(
            id=9,
            status="completed",
            generated_by_role="customer_user",
            generated_by=42,
            visible_to_customer=True,
            customer_code=CC,
            report_name="Monthly",
            date_from=datetime(2026, 9, 1),
            date_to=datetime(2026, 9, 30),
        )
        event = asyncio.run(events.report_ready_event(9, _session_with({("IncidentManagementCustomerReport", 9): report})))
        assert (event.only_user_ids, event.dedupe_key, event.title) == (frozenset({42}), "report_ready:report:9", "Report ready: Monthly")
        assert event.body == "It covers 2026-09-01 to 2026-09-30."

    @pytest.mark.parametrize(
        "status,visible,expected",
        [("completed", True, True), ("completed", False, False), ("processing", True, False)],
    )
    def test_a_soc_report_reaches_the_customer_once_shared_and_finished(self, status, visible, expected):
        report = SimpleNamespace(
            id=9,
            status=status,
            generated_by_role="analyst",
            generated_by=1,
            visible_to_customer=visible,
            customer_code=CC,
            report_name="Monthly",
            date_from=None,
            date_to=None,
        )
        event = asyncio.run(events.report_ready_event(9, _session_with({("IncidentManagementCustomerReport", 9): report})))
        assert (event is not None) is expected
        if event:
            assert event.only_user_ids is None

    def test_a_wait_is_keyed_on_the_clocks_pause(self):
        alert = SimpleNamespace(id=7, alert_name="Odd login", status="PENDING_CUSTOMER", customer_code=CC, severity="High")
        paused = datetime(2026, 10, 1, 9, 30, 12, 500)
        event = asyncio.run(events.waiting_event("alert", 7, 3, _session_with({("Alert", 7): alert}, scalar=paused)))
        assert event.dedupe_key == "waiting_on_you:alert:7:2026-10-01T09:30:12"
        assert (event.actor_user_id, event.event, event.title) == (3, "waiting_on_you", "The SOC is waiting on your reply: Odd login")

    def test_no_wait_once_the_item_moved_on(self):
        alert = SimpleNamespace(id=7, alert_name="Odd login", status="IN_PROGRESS", customer_code=CC, severity="High")
        assert asyncio.run(events.waiting_event("alert", 7, 3, _session_with({("Alert", 7): alert}))) is None

    def test_a_closing_is_keyed_on_its_time(self):
        case = SimpleNamespace(
            id=3,
            case_name="Phishing",
            case_description="x " * 400,
            case_status="CLOSED",
            customer_code=CC,
            case_closed_time=datetime(2026, 10, 1, 10, 0, 5),
        )
        event = asyncio.run(events.case_closed_event(3, None, _session_with({("Case", 3): case})))
        assert event.dedupe_key == "case_closed:case:3:2026-10-01T10:00:05"
        assert len(event.body) == events.MAX_BODY and event.body.endswith("…")

    def test_a_case_without_a_customer_notifies_nobody(self):
        case = SimpleNamespace(id=3, case_name="x", case_description="", case_status="CLOSED", customer_code=None, case_closed_time=None)
        assert asyncio.run(events.case_closed_event(3, None, _session_with({("Case", 3): case}))) is None

    @pytest.mark.parametrize(
        "entity,status,scheduled",
        [
            ("alert", "PENDING_CUSTOMER", True),
            ("case", "PENDING_CUSTOMER", True),
            ("case", "CLOSED", True),
            ("alert", "CLOSED", False),
            ("case", "IN_PROGRESS", False),
        ],
    )
    def test_only_waits_and_case_closings_are_scheduled(self, entity, status, scheduled):
        with patch.object(events, "_schedule") as schedule:
            events.notify_status_change(entity, [1], status, 5)
        assert schedule.called is scheduled

    def test_nothing_is_scheduled_without_ids(self):
        with patch.object(events, "_schedule") as schedule:
            events.notify_status_change("alert", [], "PENDING_CUSTOMER", 5)
        assert not schedule.called

    def test_scheduling_without_a_loop_is_skipped_not_raised(self):
        events.notify_alert_created(1)  # no running loop: logged, never raised


# ── Routes and hooks ──────────────────────────────────────────────────────────


def _routes():
    from copilot import app

    return {(method, route.path): route for route in app.routes if isinstance(route, APIRoute) for method in route.methods}


def _scopes(route) -> set:
    found = set()
    for dependency in route.dependant.dependencies:
        call = dependency.call
        names = getattr(call, "__closure__", None) or ()
        for cell in names:
            value = cell.cell_contents
            if isinstance(value, (tuple, list, set, frozenset)) and all(isinstance(v, str) for v in value):
                found |= set(value)
    return found


class TestRoutes:
    def test_the_bell_and_the_choices_are_portal_users_only(self):
        routes = _routes()
        for key in [
            ("GET", "/api/customer_portal/notifications"),
            ("GET", "/api/customer_portal/notifications/availability"),
            ("GET", "/api/customer_portal/notifications/preferences"),
            ("PUT", "/api/customer_portal/notifications/preferences"),
            ("GET", "/api/customer_portal/notifications/unread-count"),
            ("POST", "/api/customer_portal/notifications/read"),
        ]:
            assert _scopes(routes[key]) == {"customer_user"}, key

    def test_the_switch_is_an_operators(self):
        routes = _routes()
        assert _scopes(routes[("GET", "/api/customer_portal/notifications/settings/{customer_code}")]) == {"admin", "analyst"}
        assert _scopes(routes[("PUT", "/api/customer_portal/notifications/settings/{customer_code}")]) == {"admin"}


class TestHooks:
    """The incident and report code tells the portal, after the change is committed."""

    def test_status_routes_notify(self):
        from app.incidents.routes import db_operations as routes

        for name in ("update_alert_status_endpoint", "bulk_update_alert_status_endpoint", "update_case_status_endpoint"):
            source = inspect.getsource(getattr(routes, name))
            assert "notify_status_change(" in source, name

    def test_new_alerts_notify_after_their_tags(self):
        from app.incidents.routes import db_operations as routes
        from app.incidents.services import incident_alert

        source = inspect.getsource(incident_alert.create_alert_full)
        assert "notify_alert_created(alert_id)" in source
        assert source.index("notify_alert_created(alert_id)") > source.index("alert_created_event(")
        assert "notify_alert_created(" in inspect.getsource(routes.create_alert_endpoint)

    def test_reports_notify_when_finished_and_when_shared(self):
        from app.incidents.routes import customer_report as report_routes
        from app.incidents.services import customer_report

        assert "notify_report_ready(report.id)" in inspect.getsource(customer_report.generate_customer_report)
        assert "notify_report_ready(report_id)" in inspect.getsource(report_routes.set_report_visibility_endpoint)
