# CLAUDE.md

Repository orientation for AI coding assistants and human contributors. The notes below capture non-obvious context that's hard to reverse-engineer from the source alone — startup ordering, tenancy invariants, and footguns that have actually caught people. If you're using a tool that prefers `AGENTS.md`, symlink it to this file.

## What this is

SOCFortress CoPilot — a "single pane of glass" SOC platform that wraps open-source security tooling (Wazuh, Graylog, Velociraptor, Cortex, Grafana, InfluxDB, Shuffle, Sublime, …) plus many commercial integrations (CrowdStrike, Carbon Black, Defender, Mimecast, Huntress, Bitdefender, Darktrace, Duo, …).

Three independent apps in one repo:

- `backend/` — Python 3.11 FastAPI (port 5000) + APScheduler
- `frontend/` — Vue 3 / Vite SOC-analyst UI (Naive UI, Pinia, Tailwind, pnpm)
- `customer-portal/` — Vue 3 / Vite end-customer UI (port 3001 in dev, separate build)

Plus `tools/remotion-*` (video generators) and `docs/` (mkdocs site, published by `docs-pages.yml`).

## Common commands

### Stack

```bash
docker compose pull && docker compose up -d   # backend, frontend, mysql, minio, nuclei, mcp
./build-dockers.sh [version]                  # local image rebuild (frontend only; backend stanza commented)

# Local backend rebuild + hot-swap into the running stack (~5–8 min build):
cd backend && docker buildx build --load -t ghcr.io/socfortress/copilot-backend:latest .
docker compose up -d --force-recreate copilot-backend
# Boot signal: "Application startup complete" + "Uvicorn running on 0.0.0.0:5000"
```

`.env` at repo root feeds compose; `.env.example` documents every var.

### Backend (`cd backend`, Python 3.11)

```bash
uvicorn copilot:app --reload --port=5000      # dev
python copilot.py                             # prod-style (matches Dockerfile CMD)
pytest                                        # tests
alembic upgrade head                          # auto-runs at startup; manual when needed
alembic revision --autogenerate -m "msg"
```

`JWT_SECRET` is a hard startup gate (`backend/app/auth/utils.py`) — the app refuses to boot if unset or set to the GHSA-4gxj-hw3c-3x2x default.

### Frontend / Customer Portal (both pnpm, Node ≥ 18)

```bash
cd frontend            # or cd customer-portal — both have these scripts
pnpm dev               # vite (frontend uses Vite default port; portal forces 3001)
pnpm start             # concurrently runs backend uvicorn + this app's vite
pnpm build             # type-check + vite build
pnpm lint              # eslint --fix
pnpm type-check        # vue-tsc --build --force
pnpm format            # prettier --write src/
pnpm lint-type-format  # combined preflight
```

`pnpm test:unit` (vitest) exists only in `frontend/`; customer-portal has no test setup. Single file: `pnpm test:unit path/to/file.spec.ts`.

### Pre-commit

```bash
pre-commit run --all-files
```

Hooks: black (py3.11, **line-length 140** per `pyproject.toml`), isort (`force_single_line = true`, black profile), flake8 (`.flake8`, max-line-length 400, many `E*` ignored), `add-trailing-comma`, `setup-cfg-fmt`, eslint via `frontend/eslint.config.mjs`. The whole repo's hooks skip `backend/app/routers/__init__.py` and `backend/app/db/all_models.py`.

## Architecture

### `backend/copilot.py` startup

One FastAPI app mounts ~50 routers under `/api`. The `@app.on_event("startup")` hook runs in order:

1. (PRODUCTION env only) `create_database_if_not_exists` + `create_copilot_user_if_not_exists` — bootstraps MySQL via root creds
2. `apply_migrations()` — Alembic `upgrade head`
3. `create_buckets()` — MinIO buckets
4. `add_connectors` / `delete_connectors` — sync supported connectors into the `connectors` table
5. `create_roles`, `create_available_integrations`, `create_available_network_connectors` — seed enums
6. `ensure_admin_user`, `ensure_scheduler_user` — idempotent system users
7. `init_scheduler()` — APScheduler, started here, removed cleanly on shutdown

CORS is wide open (`allow_origins=["*"]`). Auth is per-route via `app.auth.utils.AuthHandler` (JWT). `app/middleware/exception_handlers.py` converts `HTTPException`, `RequestValidationError`, and `ValueError` into structured responses.

### Connectors vs. Integrations vs. Routers

Three sibling namespaces with distinct roles — pick the right one:

- **`app/connectors/<tool>/`** — first-party deeply-integrated tools (Wazuh indexer/manager, Graylog, Velociraptor, Cortex, Grafana, InfluxDB, Shuffle, Sublime, Portainer, Talon, event_shipper). Credentials live in the `connectors` table. The Talon connector is special — see "AI analyst pipeline" below.
- **`app/integrations/<tool>/`** — pluggable 3rd-party services (CrowdStrike, Carbon Black, Defender, Bitdefender, Mimecast, Huntress, Darktrace, Duo, Cato, Office 365, GitHub Audit, …) plus higher-level integration features (`alert_creation_settings`, `alert_escalation`, `copilot_action`, `copilot_mcp`, `copilot_searches`, `monitoring_alert`, `modules`). Auth keys are persisted per-customer (`integration_auth_keys`).
- **`app/routers/<feature>.py`** — top-level FastAPI routers that compose connectors + integrations into product features. Every router must be imported and `include_router`-ed in `copilot.py`.

### Module layout: `routes / services / schema`

Every backend module — connectors, integrations, and feature modules (`app/auth/`, `app/customers/`, `app/incidents/`, `app/network_connectors/`, …) — follows the same modular split. When adding code, keep each layer responsible for only its concern:

- **`routes/`** — FastAPI endpoints. Thin: parse/validate input, call services, shape the response. No business logic, no DB queries, no third-party SDK calls.
- **`services/`** — business logic. Talks to the DB, calls connector/integration SDKs, orchestrates work. Imported by routes and by other services.
- **`schema/`** — Pydantic / SQLModel request and response shapes. Shared between routes and services so signatures stay typed end-to-end.
- **`models/`** (when present) — SQLModel ORM tables for that module.
- **`utils/`** or `utils.py` (when present) — pure helpers with no FastAPI or DB dependency.

New modules should mirror this structure exactly — it's what the rest of the backend assumes when importing across modules and what keeps Alembic / OpenAPI generation predictable.

### Secrets that can't be rotated

`TOTP_ENCRYPTION_KEY` (Fernet, in `app/auth/services/totp.py`) — once 2FA is enrolled, rotating this key makes stored TOTP secrets unreadable. Falls back to a key derived from `JWT_SECRET`. `SSO_STATE_SECRET` similarly falls back to `JWT_SECRET`.

### AI analyst pipeline (CoPilot ↔ Talon / NanoClaw)

The "AI Analyst" feature is a *separate service*: [Talon](https://github.com/taylorwalton/talon) (also referred to as NanoClaw in its docs) — a Node.js process running an MCP-driven Claude agent that investigates SOC alerts. CoPilot is the database of record; Talon is the AI brain. Full integration spec: <https://raw.githubusercontent.com/taylorwalton/talon/refs/heads/main/docs/COPILOT_INTEGRATION.md>.

**Data flow** (both directions matter):

1. **CoPilot → Talon (outbound)** — `app/connectors/talon/` is a normal CoPilot connector. The HTTP endpoint + API key live in the `connectors` table (`TALON_URL=http://127.1.1.1:3100`, `TALON_API_KEY` per `.env.example`). `app/connectors/talon/utils/universal.py` exposes async GET/POST helpers and an SSE streaming POST. Triggers: a real-time `POST /investigate` when an alert lands, an analyst-initiated `POST /message`, plus status/job lookups (`GET /status`, `GET /jobs/:alertId`).
2. **Talon → CoPilot (inbound write-back)** — Talon's agent has *read-only* MySQL access; all writes go through CoPilot REST endpoints (mounted under `/api/ai_analyst`, lives in `app/ai_analyst/routes/`). These power the agent's MCP tools (`CreateAiAnalystJobTool`, `SubmitAiAnalystReportTool`, `SubmitAiAnalystIocsTool`, `ListAiAnalystJobsByAlertTool`, …) defined in the `copilot-mcp-server` repo.
3. **Scheduled fallback** — every 15 min Talon queries `incident_management_alert` JOIN `incident_management_asset` LEFT JOIN `ai_analyst_job` for OPEN alerts with no job row, and runs the same investigation workflow as the real-time path.

**Persisted state on the CoPilot side** lives in `app/db/universal_models.py` as the `AiAnalyst*` block — `ai_analyst_job → ai_analyst_report → ai_analyst_ioc`, plus the human-feedback tables `ai_analyst_review`, `ai_analyst_ioc_review`, and `ai_analyst_palace_lesson`. The palace-lesson table is a queue: a CoPilot async drainer POSTs queued lessons to NanoClaw's `POST /palace/lesson` (which wraps a MemPalace MCP write), then flips the row from `pending` → `ingested` and stores the returned `drawer_id` for later expiry. CoPilot never speaks to MemPalace directly — every palace interaction is proxied via NanoClaw HTTP. See "Database structure" below for the table-level shape.

**Per-customer auto-trigger** is gated by `incident_management_ai_analyst_trigger_enabled` (one row per customer; default off). Don't fire investigations for a customer whose row is missing or `enabled=false`.

### Database structure

MySQL is the primary store via async SQLAlchemy/SQLModel (`app/db/db_session.py`); SQLite fallback in `backend/settings.py`. MinIO handles object storage (`app/data_store/`). Roughly **80 SQLModel tables** spread across the codebase — the map below is the orientation aid.

**Tenancy keystone — `customers.customer_code`.** A `varchar(50)` PK on the `customers` table that is the universal tenant key. Every per-tenant feature carries it. Two enforcement levels exist in the wild and you must read carefully which one a model uses:

- **Hard FK** (`foreign_key="customers.customer_code"`) — agents, agent_vulnerabilities, vulnerability_reports, sca_reports, event_sources, enabled_dashboards, AI analyst tables, customer_notification_route, customer_shuffle_integration, github_audit_config, github_audit_report, customers_meta. Deletes/renames cascade where set up.
- **String only, no FK** — `incident_management_alert.customer_code`, `incident_management_asset.customer_code`, `incident_management_case.customer_code`, `monitoring_alerts.customer_code`, `customer_integrations.customer_code`, `customer_network_connectors.customer_code`, `custom_alert_creation_settings.customer_code`. The ingest pipeline can land alerts for codes that don't exist yet — orphaned rows are tolerated by design. Don't add a new join expecting referential integrity.

**Permissions / RBAC** (`app/auth/models/`):

- `role` — four enumerated rows: `admin=1, analyst=2, scheduler=3, customer_user=4` (see `RoleEnum`).
- `user` — bcrypt password, FK to role.
- `user_customer_access` — M2M scoping which customers a user can see.
- `user_tag_access` + `role_tag_access` — parallel allow-list ACLs against alert tags (`incident_management_alerttag.id`). Toggled globally by the singleton `incident_management_tag_access_settings` (`enabled` flag, `untagged_alert_behavior` ∈ admin_only|visible_to_all|default_tag).
- `user_totp` — Fernet-encrypted secret + bcrypt-hashed backup codes; `last_used_at` prevents replay.
- `sso_config` (singleton id=1) — Azure / Google / Cloudflare Access JWT settings. `sso_allowed_email` is the email allowlist; new SSO users default to role 2 (analyst).

**Major domain blocks** — module → core tables → tenancy enforcement:

| Domain | Where | Headline tables | Tenant FK? |
|---|---|---|---|
| Customers / agents | `app/db/universal_models.py` | `customers`, `customers_meta`, `agents`, `agent_datastore`, `agent_vulnerabilities`, `event_sources`, `enabled_dashboards` | ✅ FK |
| Auth / RBAC / 2FA / SSO | `app/auth/models/` | `user`, `role`, `user_customer_access`, `user_tag_access`, `role_tag_access`, `user_totp`, `sso_config`, `sso_allowed_email` | n/a |
| Connector credentials | `app/connectors/models.py` | `connectors`, `connectorhistory` | n/a (deployment-wide) |
| Incident management (~28 tables) | `app/incidents/models.py` | `incident_management_alert`, `_asset`, `_case`, `_ioc`, `_alerttag`, `_case_template`/`_case_task`/`_case_event`, `_threshold_alert_metadata`, `_velo_sigma_exclusion`, `_tag_access_settings`, plus `_*fieldname` ingest dictionaries | ⚠️ STRING |
| AI analyst | `app/db/universal_models.py` (`AiAnalyst*` block) + `incident_management_ai_analyst_trigger_enabled` | `ai_analyst_job` → `ai_analyst_report` → `ai_analyst_ioc`; review chain `ai_analyst_review` → `ai_analyst_ioc_review`; queue `ai_analyst_palace_lesson` | ✅ FK |
| Notification routing | `app/db/universal_models.py` | `customer_notification_route`, `notification_dispatch_log`, `customer_shuffle_integration` | ✅ FK |
| Generic integrations system | `app/integrations/models/customer_integration_settings.py` | catalog (`available_integrations`, `_auth_keys`) → activation (`customer_integrations`, `integration_subscriptions`, `integration_auth_keys`) → service def (`integration_services`, `integration_configs`) → wiring (`customer_integrations_meta`) | ⚠️ STRING |
| Network connectors | `app/network_connectors/models/network_connectors.py` | mirrors the integrations shape with `network_connectors_*` prefix | ⚠️ STRING |
| Alert creation settings | `app/integrations/alert_creation_settings/` | `custom_alert_creation_settings` → `_event_order` → `_condition`, `_event_config` | ⚠️ STRING |
| GitHub audit | `app/integrations/github_audit/model.py` | `github_audit_config` → `_report`, `_check_exclusion`, `_baseline` | indexed string |
| Sublime alerts | `app/connectors/sublime/models/alerts.py` | `sublimealerts` + child rows (`flaggedrule`, `mailbox`, `triggeredaction`, `sender`, `recipient`) | n/a |
| Wazuh ecosystem | `app/connectors/wazuh_indexer/models/`, `app/connectors/wazuh_manager/models/` | `sigma_queries`, `index_snapshot_schedules`, `disabledrule` | n/a |
| Schedulers | `app/schedulers/models/`, `app/db/universal_models.py` | `scheduled_job_metadata` (CoPilot sidecar) + `schedulerjob` (APScheduler state blob) | n/a |
| Reports / branding / misc | `app/db/universal_models.py` + module-local | `vulnerability_reports`, `sca_reports`, `customer_portal_settings`, `customer_portal_branding`, `monitoring_alerts`, `sap_siem_multiple_logins`, `license`, `license_cache`, `log_entries`, `customer_provisioning_default_settings` | mixed |

**Conventions worth knowing before writing migrations or queries:**

- **MinIO blob pointer pattern** — every MinIO-backed row carries `bucket_name`, `object_key`, `file_name`, `file_size`, `file_hash`, `content_type`. Instances: `agent_datastore` (`velociraptor-artifacts`), `vulnerability_reports`, `sca_reports`, `incident_management_case_datastore`, `incident_management_case_report_template_datastore`. The DB row is the manifest; the actual bytes are in MinIO.
- **M2M join-table naming** — `<entity>_to_<entity>` (`incident_management_alert_to_ioc`, `incident_management_alert_to_tag`). One exception: `incident_management_casealertlink` collapses the underscores and uses an explicit `PrimaryKeyConstraint`.
- **Snapshot vs reference** — `incident_management_case_task` rows are snapshot-copied from `_case_template_task` at apply time. `template_task_id` is documented as a *soft link, informational only* — editing the source template does not mutate existing case tasks. Same convention applies anywhere the table comments call something "snapshot at … time."
- **Idempotency via unique constraints** — `notification_dispatch_log` uses `UniqueConstraint(customer_code, alert_id, route_id, trigger)` and the dispatch service does INSERT…ON CONFLICT DO NOTHING. `ai_analyst_review` is unique on `(report_id, reviewer_user_id)`. `enabled_dashboards` on `(customer_code, event_source_id, library_card, template_id)`. Honor these — don't write upserts that conflict with their semantics.
- **Source-mapped ingest dictionaries** — the `incident_management_*fieldname` family (`fieldname`, `assetfieldname`, `timestampfieldname`, `alerttitlefieldname`, `iocfieldname`, `customercodefieldname`) maps per-source (`wazuh`, `velociraptor`, `office365`, …) field names to canonical ingest fields. New SIEM source = new rows in *all six* tables.
- **Connector credentials are global, integration auth keys are per-customer.** Connectors (`app/connectors/models.py:Connectors`) hold one row per first-party tool for the whole deployment. Integrations (`integration_auth_keys` via the subscription chain) hold one row per (customer, integration). The third axis — Shuffle — uses `customer_shuffle_integration.shuffle_org_id` as the per-customer differentiator while the deployment-wide `SHUFFLER_API_KEY` lives in the `connectors` table.
- **Customer Portal branding is two-layered and merged per field.** `customer_portal_settings` (singleton) is the *global default*; `customer_portal_branding` (one row per customer, `enabled` toggles it without discarding the stored logo) is an optional override. Resolution is field-by-field — an override that only sets a title still inherits the global logo and color — and lives solely in `app/customer_portal/services/branding.py` (`build_effective_branding`). **Never read either table directly**: the portal (`GET /customer_portal/settings/effective`, authenticated) and the PDF report theming (`customer_report_branding.resolve_theme(..., customer_code=…)`) both go through that service. The *public* `GET /customer_portal/settings` stays global-only on purpose — the login page has no authenticated customer yet. A portal user scoped to more than one customer (or holding the `"*"` wildcard) resolves to the global defaults rather than picking a winner.

### Detections Catalog (view layer over `rules_cache` + Wazuh)

The Detections Catalog (top-level nav, `/detection-catalog` — note URL path stays singular for backward-compat; user-facing label is plural since the Wazuh tab was added) is a discovery surface — *not* its own data store. It is **the single feature in CoPilot that deliberately introduces no new tables, no new columns, no Alembic migrations, no schema of any kind.** Everything is in-memory caches loading from sources that already exist.

**Source caches (all in `app/integrations/copilot_searches/services/`):**

- **`rules_cache`** — CoPilot Searches rule corpus, loaded from GitHub. Each rule carries `analytic_story`, `product`, `data_source`, `mitre_attack_id`, `tactics`, `type`, `references`, …
- **`wazuh_rules_cache`** — full Wazuh Manager ruleset, loaded via one `get_wazuh_rules(limit=100000)` call. 1-hour TTL (rules change only on operator action). Graceful degradation: when Wazuh is unreachable the cache holds `unavailable_reason` and `is_available=False` so the UI can render an inline warning instead of erroring.
- **`wazuh_firing_stats_cache`** — per-rule hit counts from the Wazuh **indexer** (not manager). 15-min TTL. One ES terms aggregation per refresh buckets the last 30d of alerts by `rule.id` with **three sub-aggs**: `last_7d` (filter to 7d), `last_seen` (max of `timestamp` — gives the most recent firing per rule, rendered as relative time in the modal), and the doc_count itself (30d). ~50–100 KB of buckets, sub-second response even on 100M-doc indices. **Uses an ES-native wildcard+exclusion pattern** rather than hardcoding `wazuh-alerts-*`, because real SOCFortress deployments spread alerts across vendor-/customer-prefixed indices (`office365-<code>`, `crowdstrike-<code>`, `carbonblack-<code>`, `huntress_<code>`, ad-hoc test indices — easily 1500+ on lab clusters). The pattern is `*,-.*,-_*,-wazuh-monitoring-*,-wazuh-statistics-*,-wazuh-states-*,-wazuh-vulnerabilities-*,-security-auditlog-*` — exclusions remove Wazuh internals + Kibana/OpenSearch system indices; the `*` includes everything else. A separate `_cat/indices` call runs alongside but only to populate `resolved_indices` for debug logging — the search itself uses the pattern string. Field-name fallback chain `rule.id → rule_id → id` because the index mapping varies across versions; the winning field is sticky between refreshes. Search uses `ignore_unavailable=True` and `allow_no_indices=True` so one inaccessible index doesn't fail the whole aggregation.

- **Per-customer firing slice is NOT cached** — `fetch_firing_stats_for_customer(customer_code)` runs a fresh ES aggregation per request with an extra `term` filter on `agent_labels_customer` (or `agent.labels.customer` — both shapes tried in fallback). Reason: caching every customer × rule combo would balloon memory for customers nobody is looking at. On-demand keeps the global cache lean and the per-customer query is still sub-second. The customer field uses Graylog's flat convention (`agent_labels_customer`) by default since that's what SOCFortress's pipelines produce; falls back to the nested Wazuh-vanilla shape (`agent.labels.customer`) for stock installs.
- **`mitre_matrix`** — STIX bundle file. Resolves `mitre_attack_id` → tactic display names and powers the Coverage Gaps tab.

Consequence: refreshing CoPilot Searches refreshes the Stories surface; Wazuh rules + firing stats have their own TTL'd refresh paths. There is no migration, no new table. Aggregations (group by story, project to row shape, compute coverage gaps, format synthesized XML, …) happen *fresh on each request* inside `services/detection_catalog.py`. **If you find yourself adding a database column, schema, or migration for the catalog, stop** — that's a design violation. The catalog must remain a thin projection.

**Surfaces (browse modes):**

- **CoPilot Searches tab** (URL token still `?tab=stories` for back-compat) — CoPilot Searches rules grouped by `analytic_story` tag. Click a row → story detail page (description, member detections table, deduplicated data sources / references). The story detail is its own URL state (`?story=Foo`), not a tab.
- **Wazuh Rules tab** — flat searchable grid over the entire Wazuh ruleset (~3–5k rows). Columns: ID · Level · Description · Groups · MITRE · File · Hits 30d (with 7d sub-count) when firing stats available. Quick-filter chips **All / Top noisy (50) / Dead (level ≥7, 0 hits 30d)** for tuning workflows. Customer-scope dropdown to slice firing stats by `agent_labels_customer` (or `agent.labels.customer` — both shapes tried). Row click → modal with full meta + reconstructed `<rule>` XML + "Last fired" relative timestamp.
- **Coverage Gaps tab** — MITRE techniques no rule in either corpus addresses. Sub-techniques collapsed into parents (a hit on T1059.001 counts as coverage for T1059) — listing every sub-technique would flood the gap report.
- **Compliance tab** — Wazuh rules grouped by control IDs for a selected compliance framework (PCI DSS / HIPAA / NIST 800-53 / GDPR / TSC / GPG13). Each row shows rule count + total firing hits per control. Frameworks are statically declared in `services/detection_catalog.py:COMPLIANCE_FRAMEWORKS` — adding a new one is one row in that dict + the field already being on the cached Wazuh rules.
- **Logtest panel** (collapsible, above the Wazuh table, not its own tab) — paste a raw log line, pick a `log_format`, see which Wazuh rule fires. Wraps Wazuh's `PUT /logtest` so we get real Wazuh decoder/rule-chain behavior rather than re-implementing the engine. The panel persists the **last 5 tests** to localStorage (`detectionCatalog.logtest.history`) so analysts can click any prior paste to restore the input + format without retyping.

**Rule source XML synthesis:** The Wazuh rule detail modal renders a reconstructed `<rule id="…" level="…">…</rule>` block in the "Rule Source" section. We **don't fetch** the original `.xml` file via Wazuh's `GET /rules/files/{filename}` because (a) that endpoint returns the whole file (dozens of rules per file), requiring XML parsing to extract one, and (b) it's admin-scoped while the catalog is analyst-accessible. Synthesis from cached fields (`id`, `level`, `description`, `groups`, `mitre`, compliance arrays, the free-form `details` dict) is functionally identical and avoids both problems. See `_synthesize_rule_xml` in `services/detection_catalog.py` if you need to evolve the format.

**Auth-scope sidestep pattern** (used throughout the catalog): when a catalog route needs data from an admin-only connector route, **call the underlying service function directly** rather than proxying through the connector route. Scope checks live on the route handler (the `Security(...require_any_scope("admin"))` dependency), not on the service function. The catalog's `wazuh_rules_cache.refresh()` calls `get_wazuh_rules()` directly; the catalog's logtest calls `run_logtest()` directly; both let the catalog routes stay `admin|analyst|customer_user` while the connector routes (used for management actions like enable/disable) stay locked down. If you find yourself wanting to widen the scope on an existing connector route to feed the catalog, don't — sidestep instead.

**Wiring layout** (everything stays inside the `copilot_searches` namespace on the backend and a `detectionCatalog/` namespace on the frontend):

- Backend services: `services/detection_catalog.py` (aggregators), `services/wazuh_rules_cache.py`, `services/wazuh_firing_stats_cache.py`
- Backend connector wrapper: `app/connectors/wazuh_manager/services/logtest.py` (thin `PUT /logtest` wrapper — see `send_put_request` footgun below)
- Backend routes (appended to `routes/copilot_searches.py`):
  - `GET /catalog/stats` — counts for the header strip (includes Wazuh-side counts mirrored from the cache)
  - `GET /catalog/stories` + `GET /catalog/stories/{story_name:path}` (the `:path` converter is required — story names contain spaces and punctuation)
  - `GET /catalog/wazuh-rules` (optional `?customer_code=X` for per-customer firing scope) + `GET /catalog/wazuh-rules/{rule_id}` (rule_id is `int`; route ordering matters — see route-ordering footgun)
  - `GET /catalog/coverage-gaps`
  - `GET /catalog/compliance/frameworks` (static, before wildcard) + `GET /catalog/compliance/{framework}` (framework key from `COMPLIANCE_FRAMEWORKS` dict; 400 on unknown)
  - `POST /catalog/wazuh-rules/test` — logtest
- Frontend view: `src/views/DetectionCatalog.vue` (thin wrapper) → `src/components/detectionCatalog/` directory:
  - `DetectionCatalogShell.vue` — header strip + tab switcher (URL-synced via `?tab=stories|wazuh|gaps`)
  - `StoriesIndex.vue` + `StoryDetail.vue` — the original Stories surface
  - `WazuhRulesIndex.vue` — Wazuh tab grid + quick-filter chips + customer-scope dropdown, mounts `WazuhLogTest.vue` above the table
  - `WazuhRuleDetail.vue` — Wazuh rule detail modal contents (incl. Last fired relative-time badge)
  - `WazuhLogTest.vue` — collapsible logtest panel, persists last 5 tests to localStorage
  - `CoverageGapsIndex.vue` — Coverage Gaps tab
  - `ComplianceIndex.vue` — Compliance tab (framework selector + grouped table + drill-down modal)
- Frontend supporting files: `src/types/detectionCatalog.d.ts`, `src/api/endpoints/detectionCatalog.ts`
- Three authorized cross-cutting edits and only these three: nav entry in `app-layouts/common/Navbar/items.tsx`, route in `router/index.ts`, barrel registration in `api/index.ts`. Nothing else outside the catalog namespace should change for this feature.

### Frontend essentials

- `src/api/httpClient.ts` (axios) and `src/api/sseClient.ts` (`@microsoft/fetch-event-source`) — backend traffic. Wrappers in `src/api/endpoints/`.
- `src/stores/` — Pinia with `pinia-plugin-persistedstate`, encrypted via `secure-ls`.
- Tailwind v4 + Naive UI; design tokens flow from `figma-tokens.json` via `pnpm design-tokens`.
- `@shuffleio/shuffle-mcps` is embedded as a frontend dependency for per-org Shuffle app management.

The `customer-portal/` mirrors this structure but is a leaner standalone app, served separately (its own `nginx.conf`; port 3001 dev, 8443 in compose when uncommented).

### CI (`.github/workflows/`)

- `docker.yml` — multi-arch builds → `ghcr.io/socfortress/copilot-{backend,frontend,customer-portal,mcp,nuclei-module,minio}`
- `pre-commit.yml` — runs the hooks above on PRs
- `docs-pages.yml` — mkdocs → GitHub Pages from `docs/` (`mkdocs.yml`)

## Things that bite

- **Don't edit `backend/app/routers/__init__.py` or `backend/app/db/all_models.py`** — auto-managed import aggregators, excluded from pre-commit for that reason.
- **A new router takes two edits**: the file in `app/routers/`, plus the import + `api_router.include_router(...)` in `backend/copilot.py`. Miss the second and the route silently doesn't exist.
- **Alembic autogenerate's model registry is `backend/alembic/env.py`, not `app/db/all_models.py`** — `all_models.py` has many imports commented out and is *not* what env.py loads (env.py imports models directly). **Adding a model to an existing model file is fine** (Python imports the whole module, registering every SQLModel in it). **Adding a model in a brand-new file requires an explicit import in `env.py`** — otherwise the file is never loaded and autogenerate silently skips it.
- **`incident_management_*.customer_code` is a STRING, not a foreign key.** Same for `customer_integrations`, `customer_network_connectors`, `monitoring_alerts`, `custom_alert_creation_settings`. Renaming or deleting a customer does *not* cascade. Don't write joins that assume referential integrity on these columns.
- **AsyncSession + `back_populates` = `MissingGreenlet`** in some cases. `CustomerNotificationRoute` and `NotificationDispatchLog` deliberately omit `back_populates` on their reverse relationships (with code comments explaining why) — bidirectional relationships fire implicit synchronous loads on `flush()` that fail under `AsyncSession`. When adding relationships in async-write paths, prefer one-way FKs and explicit `session.get(...)` over `back_populates`.
- **`.env` is shared across compose services.** Backend and `copilot-mcp` both read it; many MCP vars fall back to `WAZUH_*` defaults — renaming without fixing fallbacks breaks MCP wiring.
- **Black line length is 140**, not 88. **isort `force_single_line = true`** — combined imports get split.
- **Pydantic 2 strictness regressions are still surfacing across the codebase.** The repo migrated from v1 to v2; v1 was lenient where v2 errors. Three patterns to watch for:
  - **Leading-underscore field annotations get silently dropped as `PrivateAttr`.** A field like `_source: GenericSourceModel` parses as nothing — Pydantic 2 never populates it. Use `source: GenericSourceModel = Field(alias="_source")` plus `model_config = ConfigDict(populate_by_name=True)`. We've hit this on `_source` (`GenericAlertModel`) and `_client_config` (Velociraptor `Organization`).
  - **Pydantic schemas fed SQLAlchemy/SQLModel rows need `model_config = ConfigDict(from_attributes=True)`** (the rename of v1's `orm_mode`). Symptom is a 400/500 with `Input should be a valid dictionary or instance of <ClassName>` even though the input *is* an instance — Pydantic 2 enforces exact class match, and ORM-row → Pydantic-schema extraction requires this config explicitly. Audit signal: any Pydantic class that shares a name with a `SQLModel(table=True)` is suspicious. Whole chains of nested response models (`CustomerIntegrations` → `IntegrationSubscription` → `IntegrationService` → `IntegrationAuthKeys`) need it on every level when joinedload feeds them.
  - **v2 stops coercing `bool→str`, `int→str`, etc.** A schema typed `success: str` whose callers all pass `success=True` worked in v1 (silently coerced to `"True"`); v2 errors with `Input should be a valid string [type=string_type, input_value=True, input_type=bool]`. Fix the schema's type to match what callers actually pass, not the other way around.
- **`regex=` → `pattern=` is FastAPI-only.** FastAPI 0.116 deprecated `regex=` on `Query/Path/Header/Body` in favor of `pattern=`. **`sqlmodel.Field` still uses `regex=` and rejects `pattern=`** — blindly running a global rename will crashloop the backend at import time with `TypeError: Field() got an unexpected keyword argument 'pattern'`. Pydantic v2 native `Field` uses `pattern=`. Three different surfaces, three different rules; check the import before renaming.
- **`pyvelociraptor` is pure gRPC transport.** It `json.loads` whatever the Velociraptor server emits in `Response` chunks; it does no semantic deserialization. The shape is whatever the server version picks, and *can change between minor versions*. 0.75.6 changed `_client_config` from a structured object to a YAML string. Schemas for VQL outputs should default to tolerant — drop unused fields, structure only what we actually read, lean on `extra='ignore'`.
- **`elasticsearch7.exceptions.RequestError` message lives on `.info`, not `str(err)`.** `str(err)` returns only the error code (`search_phase_execution_exception`); the human-readable cause is on `err.info`. `_is_text_field_agg_error` in `app/siem/services/dashboards.py` is the canonical example — match against `err.error` for the type and `str(err.info)` for the message.
- **FastAPI route ordering inside a single router: static paths must come before wildcards.** A `@router.get("/{id}")` declared above `@router.get("/library")` will swallow `/library` and try to parse `"library"` as the `id` param, returning a 422 with `Input is not a valid integer`. We've hit this on both the Case Templates Library (`/library` vs `/{template_id}`) and the Detection Catalog (`/catalog/stats`, `/catalog/stories` vs `/catalog/stories/{story_name:path}`). When appending new routes to an existing router, scan for wildcard routes already declared and insert above them.
- **Vue JSX (`<script setup lang="tsx">`) does not use the `:` v-bind prefix.** Inside a `.vue` `<template>` you write `<NTag :bordered="false">`; inside a JSX `render: row => (...)` you write `<NTag bordered={false}>`. Mixing them up — easy when copying from one to the other — produces a Vite parser error (`Unexpected token`). The catalog's `StoriesIndex.vue` / `StoryDetail.vue` are pure-JSX render columns; the surrounding `<template>` is Vue syntax. Don't conflate.
- **SPA sub-views driven by URL query params: `push` to open, `replace` to close.** When a parent component swaps between an index view and a detail view based on a query param (`?story=Foo`), entering the detail must use `router.push` so the browser-back button lands on the index, not on whatever was open before this page. Exiting via an in-app button should use `router.replace` to avoid piling up duplicate index entries in history. Detection Catalog's `DetectionCatalogShell.vue` `openStory` / `closeStory` is the canonical pair — getting this wrong is invisible until a user complains that browser-back skips the index entirely.
- **Iconify icon collections loaded in the frontend: `carbon:`, `mdi:`, `logos:`.** `simple-icons:` and other unbundled sets render as an empty box with no console error. If you reach for `simple-icons:wazuh` or similar, either switch to a loaded set or fall back to a plain text label.
- **`app/connectors/wazuh_manager/utils/universal.py:send_put_request` form-encodes dicts even with `Content-Type: application/json`.** The helper sets the JSON content-type header but then calls `requests.put(data=<dict>)`, which `requests` URL-form-encodes (`key=value&key=value`). Wazuh sees the JSON header but a form-encoded body, tries to parse it as JSON, and 400s with `Expecting value: line 1 column 1 (char 0)`. **Fix at the call site by pre-serializing**: `send_put_request(endpoint="/logtest", data=json.dumps(payload))` — `requests` sends string bodies as-is, no encoding. The wazuh-manager `logtest.py` connector has the canonical example. Don't try to "fix" it by passing a dict and assuming JSON encoding; the helper is used by the rule-file-upload flow which expects raw bytes/XML, and changing it globally would break that path. (Cleaner long-term fix would be a `json_data=True` flag on the helper, but it touches every Wazuh integration that PUTs.)
- **Cross-branch local-DB alembic divergence is invisible until startup.** If you run a migration from a feature branch against your local DB and then switch to a different branch that lacks the migration file, `apply_migrations()` at startup crashes with `Can't locate revision identified by <hash>` — the DB's `alembic_version` table records the missing revision, alembic has no file to walk. **Safe recovery**: `git checkout <other-branch-commit> -- backend/alembic/versions/<missing-revision>_*.py` (plus any predecessors in the chain). That brings the migration *file* into the working tree without changing the DB — the schema the file describes is already applied, alembic just needs the file to recognize the state. Don't `UPDATE alembic_version` manually unless you're prepared to fight it later; don't `alembic downgrade` unless you genuinely want to drop the columns.
- **Don't assume Wazuh alerts live only in `wazuh-alerts-*`.** Real SOCFortress deployments spread alerts across vendor- and customer-prefixed indices: `office365-<customer_code>`, `crowdstrike-<customer_code>`, `carbonblack-<customer_code>`, `huntress_<customer_code>`, ad-hoc `newest-*` test indices, and so on — easily 1500+ on lab clusters. A query targeting only `wazuh-alerts-*` will miss the bulk of real traffic. Equally, `wazuh-*` is *too broad* and includes Wazuh's own internal indices (`wazuh-monitoring-*`, `wazuh-statistics-*`, `wazuh-states-*`, `wazuh-vulnerabilities-*`) — those carry `rule.id` for system/control events with Wazuh's parent-template rule IDs (2 = firewall template, 3 = ids template, 4 = web-log template) that never fire on real analyst alerts but produce massive fake hit counts. **Use ES's native wildcard+exclusion pattern**, not client-side index enumeration: `*,-.*,-_*,-wazuh-monitoring-*,-wazuh-statistics-*,-wazuh-states-*,-wazuh-vulnerabilities-*,-security-auditlog-*` passes as one short string and ES resolves it server-side. `wazuh_firing_stats_cache.py:ALERT_INDEX_PATTERN` is the canonical implementation. Integer coercion on the bucket keys naturally drops vendor-native rule IDs that aren't Wazuh-compatible, so over-including is safe.
- **Don't pass a long index list directly to `client.search(index=[...])`.** The elasticsearch7 client serializes the list as a comma-joined URL path segment. At ~1500 indices that crosses the 4096-byte HTTP line limit and you get `too_long_http_line_exception` from the server. The fix is server-side pattern resolution — pass a short string like `*,-foo-*,-bar-*` to `client.search(index=pattern)` and let ES expand it. Combine with `ignore_unavailable=True, allow_no_indices=True` so per-index permission errors and empty matches don't fail the whole call.
- **Graylog 7.0 wraps entity-creation POSTs in a `CreateEntityRequest` — CoPilot must support both 6.x and 7.x.** SOCFortress still has clients on Graylog 6. In 7.0 the create-entity endpoints changed their request body from a flat object (`{"title": ..., ...}`) to `{"entity": {...}, "share_request": null}`; **neither version accepts the other's shape**, and 7.0 *strictly rejects* unknown properties, so you cannot just always-send the wrapper. The symptom on a flat body against 7.x is a 400 `RequestError` with `"entity cannot be null"` and `reference_path: org.graylog.security.shares.CreateEntityRequest`. **Use `app/connectors/graylog/utils/universal.py:send_post_request_create_entity(endpoint, entity=...)` for any entity-creation POST** — it probes `GET /api/system` for the server's major version (cached 5 min, defaults to 6 on failure so 6.x stays byte-for-byte unchanged) and wraps only when major ≥ 7. **Exactly four endpoints CoPilot uses are wrapped** (verified against the live 7.1.2 server's OpenAPI spec): `POST /api/streams`, `POST /api/events/definitions`, `POST /api/events/notifications`, and content-pack *install* (`POST /api/system/content_packs/{id}/{rev}/installations`). **Everything else is FLAT and must keep using plain `send_post_request`** — `POST /api/system/indices/index_sets` (index-set create), content-pack *upload* (`POST /api/system/content_packs`), all `/api/system/pipelines/*` (rule, pipeline, connections/to_stream), and `/api/events/search`. **No PUT endpoint is wrapped** (`UpdateStreamRequest`, `IndexSetUpdateRequest`, `PipelineSource` are all flat), so don't touch PUTs. Wrapping a flat endpoint breaks it under 7.x's strict-property rejection just as surely as not-wrapping a wrapped one — the four-vs-rest split is load-bearing, not cosmetic. Separately, **7.0 dropped `GET /api/system/urlwhitelist` entirely** (404, not aliased) in favor of `GET /api/system/urlallowlist`; `collector.py:get_url_whitelist_entries` tries the 7.x path first and falls back to the legacy path for 6.x.
