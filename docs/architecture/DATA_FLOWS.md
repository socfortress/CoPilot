# Data Flows (AI Agent Quick Trace)

This file is for fast debugging and change planning. Each flow includes the key files and the minimum execution path.

## 1) Startup + Initialization

Entry:
- `backend/copilot.py` -> `@app.on_event("startup")`

Flow:
1. FastAPI app starts (`backend/copilot.py`).
2. DB bootstrap/migration path runs (`backend/app/db/db_setup.py`):
   - `create_database_if_not_exists` (prod)
   - `create_copilot_user_if_not_exists` (prod)
   - `apply_migrations`
3. Object storage buckets are ensured (`backend/app/data_store/data_store_setup.py:create_buckets`).
4. Seed/reference data runs:
   - connectors (`add_connectors` -> `backend/app/db/db_populate.py`)
   - roles
   - available integrations/network connectors
5. Admin + scheduler users ensured.
6. APScheduler initialized and started (`backend/app/schedulers/scheduler.py`).

## 2) Auth Request Flow

Primary token endpoint:
- `POST /api/auth/token` in `backend/app/auth/routes/auth.py`

Flow:
1. Frontend sign-in form submits credentials (`frontend/src/components/auth/SignIn.vue`).
2. API wrapper sends form-data to `/auth/token` (`frontend/src/api/endpoints/auth.ts`).
3. Backend authenticates user (`AuthHandler.authenticate_user` in `backend/app/auth/utils.py`).
4. JWT is created with role scope(s) (`encode_token` in `backend/app/auth/utils.py`).
5. Frontend stores token in auth store (`frontend/src/stores/auth.ts`).
6. Axios interceptor adds `Authorization: Bearer <token>` on later calls (`frontend/src/api/httpClient.ts`).
7. Protected backend routes validate token/scope via `AuthHandler.get_current_user` or `require_any_scope`.

## 3) Scheduler Job Execution

Core scheduler files:
- `backend/app/schedulers/scheduler.py`
- `backend/app/schedulers/routes/scheduler.py`

Flow:
1. Startup calls `init_scheduler`.
2. `initialize_job_metadata` ensures known jobs exist in DB (`JobMetadata`).
3. `schedule_enabled_jobs` loads enabled jobs and registers interval triggers.
4. At run-time APScheduler calls mapped functions (`get_function_by_name`).
5. Example job `invoke_alert_creation_collect`:
   - runs alert auto-create route logic (`backend/app/schedulers/services/invoke_alert_creation.py`)
   - updates `JobMetadata.last_success`.
6. Manual operations (`/api/scheduler/...`) can run/pause/update/delete jobs.

## 4) Connector Verify + Use

Verify dispatch path:
- `POST /api/connectors/verify/{id}` -> `backend/app/connectors/routes.py`
- dispatch map in `backend/app/connectors/services.py:get_connector_service`

Flow:
1. Frontend calls verify (`frontend/src/api/endpoints/connectors.ts`).
2. Backend fetches connector row by ID, builds response model.
3. Connector name is mapped to a service class in `service_map`.
4. Service class calls connector-specific verifier in `backend/app/connectors/<service>/utils/universal.py`.
5. DB updates `connector_verified` + `connector_last_updated`.

Use path (runtime connector client):
1. Feature route/service calls a connector client factory in `utils/universal.py`.
2. Factory pulls credentials via `get_connector_info_from_db` (`backend/app/connectors/utils.py`).
3. Downstream API requests run with those connector settings.

## 5) Alert -> Case

Alert creation and case linking paths:
- Auto/manual alert creation routes: `backend/app/incidents/routes/incident_alert.py`
- Case creation routes: `backend/app/incidents/routes/db_operations.py`
- Case creation service: `backend/app/incidents/services/db_operations.py`

Flow:
1. Alert is ingested/created (`/incident_alert/create/manual` or `/incident_alert/create/auto`).
2. Analyst (or workflow) calls `/incident_management/case/from-alert`.
3. Backend creates `Case` using alert fields (`create_case_from_alert`).
4. Backend creates join record in `CaseAlertLink` (`create_case_alert_link`).
5. Case now references the originating alert for SOC workflows and reporting.

## 6) Artifact Upload to MinIO

Two common paths:
- Generic upload: `/api/agent_data_store/upload` (`backend/app/data_store/data_store_routes.py`)
- Velociraptor collection upload: `backend/app/connectors/velociraptor/services/artifacts.py`

Velociraptor-specific flow:
1. Collection job runs and gets `flow_id`.
2. `fetch_file_from_filestore` downloads zipped results locally.
3. `upload_agent_artifact_file` uploads file to MinIO bucket `velociraptor-artifacts` with key `agent_id/flow_id/file.zip` (`backend/app/data_store/data_store_operations.py`).
4. Metadata is stored in `AgentDataStore` table.
5. UI/API can list/download/delete via `backend/app/data_store/data_store_routes.py`.
