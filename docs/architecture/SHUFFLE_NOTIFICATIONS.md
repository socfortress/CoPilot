# Notification routing — architecture

> This file was the planning doc for per-customer notification routing, written
> before any code existed. It said of itself that it "gets folded into the
> architecture set or removed when the work ships and the user-facing docs
> land." Both have now happened, so this is a short note on what it actually
> became, for developers touching the area.
>
> **User-facing setup lives in [Notifications (Admin/Operator)](../user/notifications.md).**

---

## Shape

The engine lives in `backend/app/notifications/` and follows the standard
`routes / services / schema` split, plus one addition:

```
app/notifications/
  channels/            <- one module per delivery channel
    base.py            ChannelProvider ABC, SendResult, DispatchContext
    __init__.py        CHANNEL_REGISTRY
    shuffle.py  webhook.py  resend.py  teams.py
  services/
    notifications.py   CRUD + the dispatch loop
    dispatchers.py     raw HTTP per provider
    emit.py            fire-and-forget emission from inside CoPilot
    event_builders.py  NotificationEvent construction per trigger
    resend_quota.py    throttle + monthly counter
  schema/
    events.py          NotificationEvent (the envelope)
    notifications.py   API shapes, enums, trigger sets
```

### Adding a channel

One module under `channels/` and one line in `CHANNEL_REGISTRY`. No migration,
no schema edit, and no frontend work unless the channel wants richer UX than the
generic renderer gives — the route form builds its config inputs from the JSON
Schema the provider advertises via `GET /notification_channels`.

Teams was the first channel added under this contract and needed exactly that:
a provider, a dispatcher function, a registry entry.

## The three ideas worth knowing

**`NotificationEvent` is the envelope.** Every trigger builds one; the dispatch
loop and every provider consume only that. `DispatchRequest` — Talon's wire
format, an external contract — is adapted into one at the route boundary and is
otherwise untouched.

**Scope is a tenancy boundary, not a preference.** `scope='customer'` routes
carry a `customer_code` and serve the end customer. `scope='internal'` routes
have `customer_code IS NULL` and serve the SOC. Assignment triggers resolve only
against internal routes, because telling a customer which analyst picked up
their alert is a leak. The CRUD layer enforces the invariant both ways, and
internal routes have their own endpoints (`/internal_notification_routes`)
because there is no customer code to put in the path.

**`dedupe_key` owns idempotency.** The dispatch log is unique on
`(route_id, dedupe_key)`, and the key travels on the event — so each trigger
decides its own semantics. Assignment keys include the assignee, which is what
makes reassigning A → B → A notify A again. Manual test sends carry a uuid so
they always deliver.

## Things that bite

**`emit()` must not block.** `alert_created` is on the ingest hot path. Emission
is fire-and-forget with its **own** `AsyncSession` — reusing the request-scoped
one after the response has returned raises `MissingGreenlet` — plus a bounded
timeout and a strong task reference (asyncio holds only a weak one).

**Two guards prevent notification spam.** The `alert_created` emit sits *after*
`create_alert()`'s recurrence early-return, so a repeated alert doesn't
re-notify. Assignment emits only fire when the value actually changed.

**The AI-report gate is scope-aware.** `customer_portal_ai_report_settings` is
opt-in and governs whether AI findings may reach a customer. It gates
customer-scoped routes only; internal routes are exempt, because running
investigations while keeping results in-house is a supported configuration. The
predicate is imported from `app/customer_portal/services/ai_reports.py` rather
than reimplemented, so the two enforcement points can't drift.

**A valid Resend key can answer 401.** Send-only restricted keys are the
recommended shape for a service that only sends mail. Connector verification
treats `restricted_api_key` as success — a naive "200 means healthy" check
reports a correct production key as broken.

**Teams fails silently when wrong.** A malformed payload returns `200 OK` and
displays nothing. The Adaptive Card envelope
(`{"type":"message","attachments":[…]}`) is load-bearing, as are the 28 KB size
ceiling and the ~4 req/s throttle.

**The legacy path still exists.** `handle_customer_notifications()` in
`app/incidents/services/incident_alert.py` fires the older per-customer Shuffle
*workflow* on the same event as `alert_created`. Both are opt-in and coexist
deliberately; the route form warns when a customer has both. Consolidating them
would mean migrating live customer config and remains an open follow-up.

## Not yet done

- **Secrets are stored in cleartext.** `config` holds webhook auth headers and
  Teams webhook URLs, both credentials. Encryption at rest is outstanding.
- **No digest/batching.** Every matching event sends immediately. Relevant
  mainly to email, where the free tier is 1,000/month deployment-wide.
