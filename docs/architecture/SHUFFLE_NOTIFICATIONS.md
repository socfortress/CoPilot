# Shuffle MCP integration — per-customer notification routing

Planning doc for the Shuffle integration. Lives here while the feature is in
flight; gets folded into the architecture set or removed when the work
ships and the user-facing docs land.

**Branch:** `feat/shuffle-notifications`
**Status:** Planning — no code yet.

---

## Problem

Today, every Talon investigation writes back to the CoPilot database (job,
report, IOCs). That's it. There's no per-customer notification fan-out —
if one customer wants a Slack message on every true positive and another
wants an Outlook email on Critical-only, neither path exists.

Goals:

1. Let each customer pick their own notification destinations (Slack, Outlook,
   Teams, email — eventually any of Shuffle's 3,000+ integrations).
2. Route per-customer, with severity thresholds and trigger types.
3. Don't change Talon's existing prompts or per-alert templates.
4. Keep the MCP boundary uniform — the agent should reach notifications via
   the same stdio MCP pattern it already uses for `mysql`, `opensearch`, etc.

Non-goals:

- Replacing existing CoPilot integrations (Shuffle is for outbound notifications,
  not for swapping out our connectors).
- Building our own integration catalog. We're consuming Shuffle's hosted MCP
  layer, not reinventing it.

---

## Architecture overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      CoPilot frontend (Vue)                      │
│                                                                  │
│  Customers → [Acme] → Notifications tab                          │
│   ┌───────────────────────────────────────────┐                  │
│   │ Connected integrations  ← <ShuffleMCP>    │                  │
│   │  • Slack  • Outlook  • Teams              │                  │
│   ├───────────────────────────────────────────┤                  │
│   │ Routing rules                             │                  │
│   │  • Critical+ → Slack #soc-alerts          │                  │
│   │  • High+ → Outlook ir@corp.com            │                  │
│   └───────────────────────────────────────────┘                  │
└────────────────────────┬─────────────────────────────────────────┘
                         │ REST (CoPilot DB)
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                   CoPilot backend (FastAPI)                      │
│                                                                  │
│  New tables:                                                     │
│    customer_shuffle_integrations  (per-customer Shuffle keys)    │
│    customer_notification_routes   (severity → app → destination) │
│    notification_dispatch_log      (idempotency + audit)          │
│                                                                  │
│  New routes:                                                     │
│    GET/POST  /customers/{code}/shuffle_integrations              │
│    GET/POST  /customers/{code}/notification_routes               │
│    GET       /customers/{code}/notification_dispatch_log         │
└────────────────────────┬─────────────────────────────────────────┘
                         │ read-only MCP (mysql)
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Talon (NanoClaw)                           │
│                                                                  │
│  groups/copilot/.mcp.json gains:                                 │
│    "shuffle": "/workspace/extra/shuffle-mcp/shuffle-mcp.sh"      │
│                                                                  │
│  shuffle-mcp/shuffle-mcp.py exposes:                             │
│    shuffle_list_apps(customer_code)                              │
│    shuffle_invoke(customer_code, app, input)                     │
│    shuffle_dispatch_notifications(customer_code, alert_id,       │
│                                   trigger, severity, summary)    │
│                                                                  │
│  groups/copilot/CLAUDE.md gains a single new instruction:        │
│    "After report write-back, call                                │
│     shuffle_dispatch_notifications(...) — best effort, log       │
│     failures, never fail the investigation."                     │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTP (JSON-RPC)
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Shuffle (hosted)                            │
│  https://shuffler.io/api/v1/apps/{app}/mcp                       │
│  Authorization: Bearer <per-customer Shuffle key>                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Phase 1 — Manual webhooks, no Shuffle yet

**Why first:** ships value before any third-party dependency. Validates the
table shape, the dispatch loop, and the agent's "after write-back, fan out"
instruction.

### Backend

#### Tables

```python
class CustomerNotificationRoute(SQLModel, table=True):
    __tablename__ = "customer_notification_routes"

    id: int | None = Field(default=None, primary_key=True)
    customer_code: str = Field(foreign_key="customers.customer_code", index=True)

    name: str                            # human label, e.g. "SOC team Slack #alerts"
    trigger: str                         # 'investigation_true_positive', 'severity_critical', ...
    channel: str                         # Phase 1 set: 'slack_webhook' | 'smtp_email'
    destination: str                     # webhook URL or email address
    min_severity: str                    # 'Critical' | 'High' | 'Medium' | 'Low' | 'Informational'
    format_template: str | None = None   # optional Jinja override

    enabled: bool = True

    last_dispatched_at: datetime | None = None  # denorm for UI list
    dispatch_count: int = 0                     # denorm counter
    created_by: str | None = None               # CoPilot user who added it

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

```python
class NotificationDispatchLog(SQLModel, table=True):
    __tablename__ = "notification_dispatch_log"
    __table_args__ = (
        UniqueConstraint(
            "customer_code", "alert_id", "route_id", "trigger",
            name="uq_notif_dispatch_idem",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    customer_code: str = Field(index=True)
    alert_id: int = Field(index=True)
    route_id: int = Field(foreign_key="customer_notification_routes.id")
    trigger: str

    dispatched_at: datetime = Field(default_factory=datetime.utcnow)
    status: str                                 # 'sent' | 'failed' | 'skipped'
    error_message: str | None = None
    latency_ms: int | None = None
    payload_preview: str | None = None          # first 500 chars, debugging
```

#### Deferred / dropped

- **`anonymize`** — dropped. Recipients are SOC analysts who already see
  deanonymized reports in the UI; toggle has no consumer.
- **`tags`**, **`payload_filter`**, **`rate_limit_per_minute`** — deferred.
  `trigger` + `min_severity` covers the 80% case. Phase 4 can layer on
  richer filters / rate limits without touching this schema (rate limit
  derivable from a windowed count over the dispatch log).

#### Wiring

- Alembic migration creates both tables
- Pydantic schemas in `app/notifications/schema.py`
- CRUD service + REST routes (`/customers/{code}/notification_routes`)
- Initial dispatch helpers: `dispatch_slack_webhook(url, payload)`,
  `dispatch_smtp_email(to, subject, body)` — plain HTTP/SMTP, no Shuffle
- Logger writes to `notification_dispatch_log` with the unique-index
  upsert pattern for idempotency

### Frontend

- Customer detail page → new "Notifications" tab
- Form: pick channel (Slack/email), enter webhook URL or email, severity
  threshold, trigger type
- List view of existing routes with enable/disable toggle
- Dispatch log viewer (read-only)

### Talon

- Add a single new section to `groups/copilot/CLAUDE.md`:
  > **After report write-back**, query `customer_notification_routes` for the
  > alert's `customer_code` filtered by trigger and severity. For each
  > enabled row, format the summary per the route's template (default:
  > severity + alert link + summary) and POST the webhook / send the email.
  > Notifications are **best-effort** — log success/failure to
  > `notification_dispatch_log` keyed by `(customer_code, alert_id, route_id,
  > trigger)`. Skip if the log already has a row for that key (idempotency).
  > Do **not** fail the investigation on dispatch errors.
- The agent uses its existing tools (MySQL MCP for the route lookup + log
  write, Bash with curl for the webhook POST). No new Talon-side MCP yet.

### Acceptance

- Configure a Slack webhook for one customer
- Trigger an investigation that resolves true-positive Critical
- Slack message arrives within ~10s of report write-back
- `notification_dispatch_log` has the row
- Re-running the same investigation does not re-fire the Slack message

---

## Phase 2 — Shuffle proxy MCP in Talon

**Why:** unlocks the 3,000+ catalog without forcing the agent to learn each
provider's REST API. Single stdio MCP, same boundary as `mysql-mcp.sh`.

### Talon

- New directory: `nanoclaw/shuffle-mcp/`
  - `shuffle-mcp.sh` — bash wrapper (loads `.env`, exec's the python entry)
  - `shuffle-mcp.py` — stdio MCP server using the standard MCP Python SDK
  - `setup.sh` — install/activate per the existing pattern
  - `CLAUDE.md` — short tool-selection guide for the agent
- Tools exposed:

  | Tool | Purpose |
  |------|---------|
  | `shuffle_list_apps(customer_code)` | Return the customer's authenticated apps + a one-line description from the Shuffle catalog. Used at runtime so the agent picks intelligently. |
  | `shuffle_invoke(customer_code, app, input)` | POST to `https://shuffler.io/api/v1/apps/{app}/mcp` with the customer's Bearer key. `input` is the natural-language string Shuffle expects. |
  | `shuffle_dispatch_notifications(customer_code, alert_id, trigger, severity, summary)` | High-level convenience: looks up routes for the customer, formats per channel, calls `shuffle_invoke` for each, writes the dispatch log. Idempotent. |

- API key sourcing: the MCP queries CoPilot's MySQL for
  `customer_shuffle_integrations.api_key WHERE customer_code = ?`. **Never**
  trusts a `customer_code` parameter from the agent for cross-tenant lookups
  — the MCP enforces the tenant boundary, not the prompt.
- Container build: install `shuffle-mcp` into a venv via
  `container/Dockerfile`, like the existing `opensearch-mcp` / `mempalace`
  pattern.

### CoPilot backend

- Alembic migration: `customer_shuffle_integrations`
  - `id`, `customer_code` (FK), `app` (text, e.g. "slack"),
    `display_name`, `api_key` (encrypted), `connected_at`, `last_used_at`,
    `enabled`
- REST: CRUD for integrations + a "test" route that calls Shuffle to verify
  the key works (`tools/list` against the app's MCP endpoint)
- `customer_notification_routes` gains a `shuffle_app` column referencing
  the integration. Phase 1's manual `channel`/`destination` columns become
  optional — routes use one or the other.

### Talon prompt change

Replace Phase 1's "POST the webhook" instruction with:

> **After report write-back**, call
> `shuffle_dispatch_notifications(customer_code, alert_id, trigger,
> severity, summary)`. The MCP handles routing, formatting, and the
> dispatch log internally. Best-effort — failures already logged.

Single tool call from the agent's perspective. The MCP owns the per-channel
formatting + idempotency + tenant scoping.

### Acceptance

- Manually insert a row in `customer_shuffle_integrations` for one customer
  with a real Shuffle API key
- Investigation completes → agent calls
  `shuffle_dispatch_notifications` → Slack message arrives via Shuffle (not
  via raw webhook)
- Verify the dispatch log entry shows `app=slack` and references the
  Shuffle integration row, not a raw URL

---

## Phase 3 — Shuffle picker in CoPilot frontend

**Why:** removes the manual API key paste. Customers self-serve via the
embedded picker.

### Frontend

- Install `@shuffleio/shuffle-mcps` (peer deps already met by Vue side via
  the Vue export `@singulio/singul/vue`)
- Replace the manual "API key" input on the Notifications tab with the
  `<ShuffleMCP>` (or Vue equivalent) component
- On `onAppSelected`, kick off Shuffle's OAuth flow, capture the resulting
  Bearer key, POST it to CoPilot's `/customers/{code}/shuffle_integrations`
- Show connected integrations as cards; "Disconnect" button revokes the
  CoPilot row (does not revoke at Shuffle — admin must do that themselves
  via shuffler.io)

### Backend

- No schema change — the picker just writes through the existing
  `customer_shuffle_integrations` endpoint
- Optional: webhook receiver for Shuffle revocation events (later)

### Acceptance

- A customer admin opens the Notifications tab → clicks "+ Add integration"
  → picker shows 3,000+ apps → picks Slack → OAuth pops → returns a key
  stored in CoPilot
- A new notification route can immediately reference this integration

---

## Phase 4 — Hardening

- **Per-channel format templates:** Slack gets compact + thread, email gets
  full markdown, Teams gets adaptive card. Default templates in
  `shuffle-mcp/templates/{channel}.j2`. Routes can override via
  `format_template`.
- **Retry semantics:** failed dispatches retry once after 30s, then mark
  failed. Logged in `notification_dispatch_log.status='failed'` with the
  upstream error.
- **Audit trail UI:** Customer → Notifications → Dispatch log tab shows
  recent fires, status, retry count.
- **Rate limiting per customer:** prevent runaway dispatch storms (e.g. a
  detection rule firing 100x/min) — coalesce to 1 dispatch per minute per
  route, summarize the rest.

---

## Cross-cutting concerns

| Concern | Decision |
|---------|----------|
| **Tenant isolation** | The Shuffle MCP itself is a stateless adapter — same `/apps/slack` URL for every customer. Isolation lives in two CoPilot-side places: (1) which `customer_shuffle_integrations.api_key` row gets fetched (Bearer token differs per customer's OAuth-issued workspace), (2) which `customer_notification_routes.destination` (channel name / email) is used. Both are filtered by `customer_code` at lookup time — single SQLAlchemy boundary. Cross-tenant leak risk is "did the lookup pull the right customer's row" — covered by the FK + an explicit test. |
| **Shuffle outage** | Notification step wrapped in try/except; failure does not fail the investigation. Logged to `notification_dispatch_log.status='failed'`. |
| **PII** | Recipients are SOC analysts who already see deanonymized reports in the CoPilot UI. No anonymization layer needed. The `anonymize` column from earlier drafts has been dropped. |
| **Idempotency** | Unique index on `(customer_code, alert_id, route_id, trigger)`. Agent's instruction is "skip if log row already exists." Re-runs are safe. |
| **Format mismatch** | Default templates per channel. Custom override per route via `format_template`. Phase 4 ships the default template set. |
| **Cost** | Shuffle's per-call pricing exists but isn't blocking — revisit once we have real volume. Phase 4's coalescing/rate-limit work covers it preemptively if needed. |
| **Failure mode visibility** | `notification_dispatch_log` is the source of truth. Frontend surfaces it. |

---

## Open questions

1. **Shuffle key revocation** — does Shuffle expose a webhook when a user
   revokes upstream? Need this for clean state in CoPilot.
2. **Shuffle's `tools/list` schema** — does each app expose typed tool
   schemas, or only the natural-language `tool_name` + `input` shape? If
   typed, Phase 2 can register N tools per app instead of one generic
   `shuffle_invoke`. Worth a 30-min spike before locking Phase 2's design.

---

## Out of scope (for now)

- Inbound: Talon receiving messages back through Shuffle (Shuffle → Talon).
  Possible future use: slash commands in Slack to trigger investigations.
  Not Phase 1–4.
- Replacing CoPilot's existing alerting (Graylog → CoPilot).
- Bidirectional state (closing an alert from Slack).

---

## Summary of phasing

| Phase | Duration estimate | Ships |
|-------|-------------------|-------|
| **1** | ~3 days | Working notifications via plain webhooks/SMTP. Schema + agent loop validated. |
| **2** | ~3 days | Shuffle MCP in Talon. 3,000+ apps reachable via the catalog. |
| **3** | ~2 days | Picker in CoPilot. Customer self-service. |
| **4** | ~3 days | Templates, anonymize, retry, audit, rate limit. |

Total ~11 working days end-to-end. Phase 1 is the only one that materially
touches Talon's prompt; Phases 2–4 are additive on the MCP / DB / UI sides.
