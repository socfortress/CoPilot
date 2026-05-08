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
| Reports / branding / misc | `app/db/universal_models.py` + module-local | `vulnerability_reports`, `sca_reports`, `customer_portal_settings`, `monitoring_alerts`, `sap_siem_multiple_logins`, `license`, `license_cache`, `log_entries`, `customer_provisioning_default_settings` | mixed |

**Conventions worth knowing before writing migrations or queries:**

- **MinIO blob pointer pattern** — every MinIO-backed row carries `bucket_name`, `object_key`, `file_name`, `file_size`, `file_hash`, `content_type`. Instances: `agent_datastore` (`velociraptor-artifacts`), `vulnerability_reports`, `sca_reports`, `incident_management_case_datastore`, `incident_management_case_report_template_datastore`. The DB row is the manifest; the actual bytes are in MinIO.
- **M2M join-table naming** — `<entity>_to_<entity>` (`incident_management_alert_to_ioc`, `incident_management_alert_to_tag`). One exception: `incident_management_casealertlink` collapses the underscores and uses an explicit `PrimaryKeyConstraint`.
- **Snapshot vs reference** — `incident_management_case_task` rows are snapshot-copied from `_case_template_task` at apply time. `template_task_id` is documented as a *soft link, informational only* — editing the source template does not mutate existing case tasks. Same convention applies anywhere the table comments call something "snapshot at … time."
- **Idempotency via unique constraints** — `notification_dispatch_log` uses `UniqueConstraint(customer_code, alert_id, route_id, trigger)` and the dispatch service does INSERT…ON CONFLICT DO NOTHING. `ai_analyst_review` is unique on `(report_id, reviewer_user_id)`. `enabled_dashboards` on `(customer_code, event_source_id, library_card, template_id)`. Honor these — don't write upserts that conflict with their semantics.
- **Source-mapped ingest dictionaries** — the `incident_management_*fieldname` family (`fieldname`, `assetfieldname`, `timestampfieldname`, `alerttitlefieldname`, `iocfieldname`, `customercodefieldname`) maps per-source (`wazuh`, `velociraptor`, `office365`, …) field names to canonical ingest fields. New SIEM source = new rows in *all six* tables.
- **Connector credentials are global, integration auth keys are per-customer.** Connectors (`app/connectors/models.py:Connectors`) hold one row per first-party tool for the whole deployment. Integrations (`integration_auth_keys` via the subscription chain) hold one row per (customer, integration). The third axis — Shuffle — uses `customer_shuffle_integration.shuffle_org_id` as the per-customer differentiator while the deployment-wide `SHUFFLER_API_KEY` lives in the `connectors` table.

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
