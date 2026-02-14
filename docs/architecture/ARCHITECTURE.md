# SOCFortress CoPilot Architecture

## Overview
CoPilot is a “single pane of glass” security operations platform. It centralizes data from Wazuh, Graylog, Velociraptor, Grafana, InfluxDB, and other tools, provides alert/case management, and adds automation such as scheduled collectors, active response, and report generation. The backend is a FastAPI service with a MySQL database and MinIO object storage. The UI is a Vue 3 SPA, with an optional customer-facing portal.

Key entry points:
- Backend runtime: `backend/copilot.py`
- Frontend app: `frontend/src`
- Customer portal app: `customer_portal/src`

## Tech Stack

### Backend
- FastAPI, Starlette, Uvicorn: API server and routing. `backend/copilot.py`
- SQLModel + SQLAlchemy: ORM and DB access. `backend/app/db`
- Alembic: DB migrations. `backend/alembic`
- APScheduler: background job scheduling. `backend/app/schedulers/scheduler.py`
- MySQL: primary database. `docker-compose.yml`, `backend/app/db/db_session.py`
- MinIO: object storage for case/report artifacts, sysmon configs, Velociraptor artifacts. `backend/app/data_store`
- Loguru: logging. `backend` modules
- Requests/HTTPX: integrations with external systems. `backend/app/connectors/*/utils`, `backend/app/integrations/*`

### Frontend
- Vue 3 + TypeScript + Vite: SPA. `frontend/package.json`, `frontend/src`
- Pinia: state management. `frontend/src/stores`
- Naive UI + Tailwind CSS: UI components and styling. `frontend/package.json`, `frontend/tailwind.config.js`
- Axios: API client. `frontend/src/api`
- Cypress + Vitest: tests. `frontend/cypress`, `frontend/vitest.config.ts`

### Customer Portal (Optional)
- Vue 3 + Vite + Pinia + Naive UI. `customer_portal/package.json`, `customer_portal/src`

## Directory Layout & Responsibilities

### Root
- `docker-compose.yml`: default deployment stack (backend, frontend, MySQL, MinIO, MCP, Nuclei).
- `.env.example`: required runtime configuration for connectors and services.
- `build-dockers.sh`: build utility script.

### Backend
- `backend/copilot.py`: application entrypoint, API router mount, startup/shutdown hooks.
- `backend/settings.py`: local env loading (not the primary runtime env in Docker).
- `backend/app/routers/*`: API route modules for each feature/integration.
- `backend/app/auth/*`: authentication, user/role management.
- `backend/app/db/*`: sessions, migrations, bootstrapping, and data seeding.
- `backend/app/schedulers/*`: APScheduler instance, scheduled jobs, job metadata models.
- `backend/app/connectors/*`: connectors for platform services (Wazuh, Graylog, Grafana, etc.).
- `backend/app/integrations/*`: third‑party integrations and per‑customer integration config.
- `backend/app/network_connectors/*`: “network connectors” with customer‑scoped auth keys and configs.
- `backend/app/customer_provisioning/*`: provisioning workflows for external services (Graylog, Grafana, Portainer, Wazuh manager).
- `backend/app/stack_provisioning/graylog/*`: content packs, pipelines, streams, and input templates for Graylog.
- `backend/app/agents/*`: Wazuh and Velociraptor agent management, SCA, vulnerabilities.
- `backend/app/incidents/*`: incident management (cases, alerts, tags, reports).
- `backend/app/active_response/*`: automation scripts and invoke endpoints.
- `backend/app/data_store/*`: MinIO storage (cases, templates, artifacts).
- `backend/app/threat_intel/*`: EPSS, VirusTotal, SOCFortress threat intel.
- `backend/app/integrations/copilot_mcp/*`: local and cloud MCP queries.

### Frontend
- `frontend/src/router/index.ts`: primary navigation and feature routes.
- `frontend/src/api/endpoints/*`: typed API clients for each backend domain.
- `frontend/src/components/*`: feature UI modules (alerts, cases, agents, connectors, integrations, etc.).
- `frontend/src/views/*`: route views; corresponds closely to backend feature areas.
- `frontend/.env.example`: API base URL and UI behavior.

### Customer Portal
- `customer_portal/src/router/index.ts`: simple login + alerts/cases/agents views.
- `customer_portal/src/views/*`: customer‑limited UI.

## Core Runtime Flows

### Startup
1. `backend/copilot.py` loads env vars and initializes FastAPI.
2. On startup event:
   - Creates MySQL database and user if needed. `backend/app/db/db_setup.py`
   - Applies Alembic migrations. `backend/app/db/db_setup.py`
   - Creates MinIO buckets. `backend/app/data_store/data_store_setup.py`
   - Seeds connectors, roles, available integrations, available network connectors. `backend/app/db/db_setup.py`, `backend/app/db/db_populate.py`
   - Ensures admin and scheduler users. `backend/app/db/db_setup.py`
   - Initializes APScheduler and schedules enabled jobs. `backend/app/schedulers/scheduler.py`
3. Static mount: `scoutsuite-report` directory for cloud security assessment outputs. `backend/copilot.py`

### Auth & Authorization
- JWT auth with OAuth2 password flow. `backend/app/auth/utils.py`
- Roles/scopes: `admin`, `analyst`, `scheduler`, `customer_user`.
- Routes use `Security(AuthHandler().get_current_user, scopes=[...])` or `require_any_scope(...)`.

### API Routing
- `FastAPI` app mounts a single APIRouter at `/api`.
- Each domain lives in `backend/app/routers/*.py` and delegates to feature modules in `backend/app/<domain>/*`.
- Frontend API clients match route structure. `frontend/src/api/endpoints/*`

### Background Jobs
- APScheduler runs inside the FastAPI app.
- Job metadata is stored in MySQL and loaded on startup. `backend/app/schedulers/scheduler.py`
- Jobs invoke integration collectors and internal maintenance:
  - Agent sync (Wazuh + Velociraptor)
  - Wazuh index resize
  - Alert creation collection
  - Snapshot schedule execution
  - Integration collectors (Duo, Darktrace, Cato, Huntress, Carbon Black, etc.)
- Job definitions live in `backend/app/schedulers/services/*`.

### Integrations & Connectors
- Connectors are core service connections (Wazuh, Graylog, Grafana, etc.) stored in `Connectors` DB table.
- Connectors are seeded from env vars on startup. `backend/app/db/db_populate.py`
- Each connector implements a verify function in `backend/app/connectors/<service>/utils/universal.py` and is mapped in `backend/app/connectors/services.py`.
- Integration settings are customer‑scoped and stored in `CustomerIntegrations` / `CustomerIntegrationsMeta` tables.

### Data Storage
- MySQL for all operational data (users, integrations, connectors, alerts/cases, scheduler metadata).
- MinIO for case artifacts, report templates, sysmon configs, Velociraptor artifacts. `backend/app/data_store`
- Local filesystem: `scoutsuite-report` directory for report outputs.

## Major User‑Facing Features (Admin UI)
- Overview dashboard and system health.
- Connectors management (test/verify/update).
- Wazuh management: rules, groups, Sysmon config, MITRE browsing.
- Graylog management, metrics, pipelines, streams, inputs.
- Alerts and SIEM views, MITRE/Atomic Red Team views.
- Incident management: sources, alerts, cases, tags, comments, reports, data store.
- Agents (Wazuh + Velociraptor), SCA, vulnerabilities, data store.
- Artifacts and file collection.
- Active response actions.
- External services: third‑party integrations and network connectors.
- Reporting (Grafana dashboards, case reports, vuln/SCA reports).
- Scheduler management.
- Cloud security assessment (ScoutSuite).
- Web vulnerability assessment (Nuclei).
- GitHub Audit.
- Customer portal branding/settings.
- License management.

## Customer Portal Features
- Login and role‑restricted access for `customer_user`.
- Views for alerts, cases, case details, and agents.
- Separate SPA served by `copilot-customer-portal` container.

## Integrations & Open Source Services

### Wazuh
- Connector: `backend/app/connectors/wazuh_manager/*` and `backend/app/connectors/wazuh_indexer/*`
- Auth: API token cached in memory with TTL; requests via `requests`.
- Wazuh manager routes: `backend/app/connectors/wazuh_manager/routes/*` and `backend/app/routers/wazuh_manager.py`.
- Wazuh indexer routes: `backend/app/connectors/wazuh_indexer/routes/*`.

### Graylog
- Connector: `backend/app/connectors/graylog/*`
- Event shipper: GELF TCP to Graylog input. `backend/app/connectors/event_shipper/*`, `backend/app/integrations/utils/event_shipper.py`
- Graylog provisioning: content packs, pipelines, streams, inputs. `backend/app/stack_provisioning/graylog/*`
- Graylog API management used in routes and service modules.

### Grafana
- Connector: `backend/app/connectors/grafana/*`
- Reporting endpoints for orgs/dashboards/panels and iframe generation. `backend/app/routers/grafana.py`, `frontend/src/components/reportCreation`

### Velociraptor
- Connector: `backend/app/connectors/velociraptor/*`
- Agent management + artifacts; artifacts also stored in MinIO. `backend/app/agents/velociraptor/*`, `backend/app/data_store`

### Shuffle
- Connector: `backend/app/connectors/shuffle/*`
- Endpoints for Shuffle metadata. `backend/app/routers/shuffle.py`

### InfluxDB
- Connector: `backend/app/connectors/influxdb/*`
- Healthcheck and monitoring endpoints. `backend/app/routers/influxdb.py`, `frontend/src/components/healthcheck`

### Portainer
- Connector: `backend/app/connectors/portainer/*`
- Customer provisioning workflows can call Portainer. `backend/app/customer_provisioning/services/portainer.py`

### Nuclei
- Integration: `backend/app/integrations/nuclei/*` and `backend/app/routers/nuclei.py`
- Container present in `docker-compose.yml` as `copilot-nuclei-module`.

### ScoutSuite
- Integration: `backend/app/integrations/scoutsuite/*` and `backend/app/routers/scoutsuite.py`
- Outputs served from `scoutsuite-report` static mount.

### Threat Intel
- VirusTotal, EPSS, SOCFortress. `backend/app/threat_intel/*`

### MCP (CoPilot AI)
- Local MCP service container configured in Docker.
- Backend routes call `backend/app/integrations/copilot_mcp/services/copilot_mcp.py` to query local OpenSearch/MySQL/Wazuh/Velociraptor or cloud threat intel endpoints.

## Configuration Management & Secrets
- `.env` provides connector URLs, API keys, DB creds, MinIO creds, MCP settings. `.env.example` documents expected values.
- Frontend uses `VITE_API_URL` to target the backend.
- TLS handled by `copilot-frontend` container; TLS cert/key paths are configurable in `docker-compose.yml` and documented in README.

## Deployment (Docker Compose)
- `copilot-backend`: FastAPI service on port 5000.
- `copilot-frontend`: Vue app with TLS, ports 80/443.
- `copilot-mysql`: MySQL 8.
- `copilot-minio`: object storage.
- `copilot-nuclei-module`: web vulnerability scanner module.
- `copilot-mcp`: MCP service for AI queries.
- Optional `copilot-customer-portal` for customer‑facing UI.

## Extension Points

### Add a New Connector
1. Add connector metadata in `backend/app/db/db_populate.py`.
2. Add verification logic in `backend/app/connectors/<new_service>/utils/universal.py`.
3. Map the connector name in `backend/app/connectors/services.py`.
4. Provide routes in `backend/app/connectors/<new_service>/routes` and `backend/app/routers/<new_service>.py` as needed.
5. Add frontend UI and API client in `frontend/src/components` and `frontend/src/api/endpoints`.

### Add a New Integration (Per‑Customer)
1. Add integration metadata in `backend/app/db/db_populate.py`.
2. Add models/schema in `backend/app/integrations/models` and `backend/app/integrations/schema`.
3. Add integration service/routes in `backend/app/integrations/<integration_name>`.
4. Expose route in `backend/app/routers/<integration_name>.py`.
5. Add scheduled collection jobs if needed: `backend/app/schedulers/services/*` and `backend/app/schedulers/scheduler.py`.

### Add a New Scheduler Job
1. Implement job function in `backend/app/schedulers/services`.
2. Add to `known_jobs` in `backend/app/schedulers/scheduler.py`.
3. Add function mapping in `get_function_by_name`.
4. Expose job control in `backend/app/schedulers/routes/scheduler.py`.

### Add a New Customer Portal Feature
1. Add backend route with `customer_user` role scope.
2. Add UI in `customer_portal/src/views` and wire in `customer_portal/src/router/index.ts`.
