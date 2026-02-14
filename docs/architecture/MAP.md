# CoPilot Repo Map

## Root
- `README.md`  
  High‑level product overview, install steps, and TLS notes.
- `docker-compose.yml`  
  Deployment stack for backend, frontend, MySQL, MinIO, MCP, and Nuclei.
- `.env.example`  
  Canonical list of backend environment variables and connector settings.
- `build-dockers.sh`  
  Build helper for Docker images.

## Backend Entry & Config
- `backend/copilot.py`  
  FastAPI app initialization, router mounting, startup/shutdown orchestration.
- `backend/settings.py`  
  Local env loading; legacy settings for SQLAlchemy URI.
- `backend/requirements.txt`  
  Backend dependencies including FastAPI, SQLModel, APScheduler, integrations.

## Database & Migrations
- `backend/app/db/db_session.py`  
  Async and sync SQLAlchemy engines, session management.
- `backend/app/db/db_setup.py`  
  DB creation, migrations, seeding, admin/scheduler user creation.
- `backend/app/db/db_populate.py`  
  Default connectors, integrations, roles, auth keys.
- `backend/alembic/`  
  Alembic migrations and config.

## Auth & Middleware
- `backend/app/auth/utils.py`  
  JWT auth, scopes/roles enforcement.
- `backend/app/auth/models/users.py`  
  User and role models.
- `backend/app/middleware/*`  
  License gating, logging, customer access control, exception handling.

## Core Routing
- `backend/app/routers/`  
  Route modules for every domain (connectors, agents, incidents, integrations, etc.).

## Scheduler & Jobs
- `backend/app/schedulers/scheduler.py`  
  APScheduler setup, job metadata, scheduling logic.
- `backend/app/schedulers/routes/scheduler.py`  
  API endpoints to list/update jobs.
- `backend/app/schedulers/services/`  
  Collectors and scheduled tasks (alert creation, Cato, Duo, Darktrace, etc.).

## Connectors (Platform Services)
- `backend/app/connectors/routes.py`  
  Connector CRUD and verification API.
- `backend/app/connectors/services.py`  
  Connector verification dispatch map and file upload handling.
- `backend/app/connectors/utils.py`  
  Shared DB lookup helpers for connectors.
- `backend/app/connectors/wazuh_manager/`  
  Wazuh Manager auth/token caching and request utilities.
- `backend/app/connectors/wazuh_indexer/`  
  Wazuh Indexer connection utilities.
- `backend/app/connectors/graylog/`  
  Graylog API helpers and routing.
- `backend/app/connectors/grafana/`  
  Grafana connection utilities and folder/datasource management.
- `backend/app/connectors/velociraptor/`  
  Velociraptor connection and API helpers.
- `backend/app/connectors/shuffle/`  
  Shuffle connection verification.
- `backend/app/connectors/event_shipper/`  
  GELF TCP logger for Graylog event shipping.
- `backend/app/connectors/portainer/`  
  Portainer connection utilities.

## Integrations (Per‑Customer)
- `backend/app/integrations/routes.py`  
  Customer integration CRUD and validation.
- `backend/app/integrations/models/customer_integration_settings.py`  
  Integration config and auth key models.
- `backend/app/integrations/modules/`  
  Data collection modules for Duo, Darktrace, Mimecast, Huntress, etc.
- `backend/app/integrations/copilot_mcp/`  
  MCP query routing (local and cloud services).
- `backend/app/integrations/nuclei/`  
  Web vulnerability assessment.
- `backend/app/integrations/scoutsuite/`  
  Cloud security assessment.
- `backend/app/integrations/github_audit/`  
  GitHub audit reports and metadata.

## Network Connectors
- `backend/app/network_connectors/routes.py`  
  Customer‑scoped “network connector” management and auth keys.
- `backend/app/network_connectors/models/network_connectors.py`  
  Network connector DB schema and relations.

## Provisioning
- `backend/app/customer_provisioning/services/`  
  Provision/decommission Graylog, Grafana, Wazuh, Portainer for customers.
- `backend/app/stack_provisioning/graylog/`  
  Graylog content packs, pipelines, streams, inputs templates.

## Incidents & SOC Features
- `backend/app/incidents/`  
  Incident alerts/cases, reports, tags, and case data store.
- `backend/app/agents/`  
  Wazuh/Velociraptor agents, SCA, vulnerabilities, data store.

## Data Store
- `backend/app/data_store/data_store_session.py`  
  MinIO client factory.
- `backend/app/data_store/data_store_setup.py`  
  Buckets for cases, templates, sysmon configs, Velociraptor artifacts.

## Active Response
- `backend/app/active_response/`  
  Active response routes and scripts (Windows/Linux).

## Threat Intel
- `backend/app/threat_intel/`  
  EPSS, VirusTotal, SOCFortress threat intel routes/services.

## Frontend (Admin UI)
- `frontend/src/router/index.ts`  
  Primary UI routes and feature pages.
- `frontend/src/api/endpoints/`  
  Typed API clients for backend endpoints.
- `frontend/src/components/`  
  Feature components: alerts, cases, agents, connectors, integrations, reports.
- `frontend/.env.example`  
  Vite environment defaults.

## Customer Portal
- `customer_portal/src/router/index.ts`  
  Customer portal routes (login, alerts, cases, agents).
- `customer_portal/src/views/`  
  Customer‑facing views with limited features.
