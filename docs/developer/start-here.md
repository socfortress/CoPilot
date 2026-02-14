# AI Agent Docs Entrypoint

This folder is the **starting point for AI agents** making code changes in this repo.

## Read This First

1. `docs/architecture/ARCHITECTURE.md` (existing system architecture)
2. `docs/architecture/MAP.md` (existing system map)
3. `docs/architecture/DEPLOYMENT.md` (runtime stack, ports, env, persistence)
4. `docs/architecture/DATA_FLOWS.md` (critical request + job + data flows)
5. `docs/integrations/ADDING_A_CONNECTOR.md` (exact connector extension checklist)

## Fast Repo Orientation (Code Pointers)

- Backend entrypoint: `backend/copilot.py`
- Backend router registration: `backend/copilot.py`, `backend/app/routers/*.py`
- DB bootstrap + seed logic: `backend/app/db/db_setup.py`, `backend/app/db/db_populate.py`
- Connector registry + verify dispatch: `backend/app/connectors/services.py`
- Connector DB lookup helper: `backend/app/connectors/utils.py`
- Auth routes + JWT handling: `backend/app/auth/routes/auth.py`, `backend/app/auth/utils.py`
- Scheduler init + job mapping: `backend/app/schedulers/scheduler.py`
- Scheduler APIs: `backend/app/schedulers/routes/scheduler.py`
- Incident alert/case paths: `backend/app/incidents/routes/incident_alert.py`, `backend/app/incidents/routes/db_operations.py`, `backend/app/incidents/services/db_operations.py`
- MinIO data store operations: `backend/app/data_store/data_store_operations.py`, `backend/app/data_store/data_store_setup.py`, `backend/app/data_store/data_store_session.py`
- Frontend API client base: `frontend/src/api/httpClient.ts`
- Frontend connector endpoints + UI: `frontend/src/api/endpoints/connectors.ts`, `frontend/src/views/Connectors.vue`, `frontend/src/components/connectors/*`

## Agent Guardrails

- Prefer editing the smallest set of files that completes the task.
- When adding backend functionality, wire all layers explicitly:
  1. service/util
  2. route
  3. router include
  4. top-level include in `backend/copilot.py`
- When adding user-facing connector features, update both:
  - backend endpoint(s)
  - frontend endpoint wrapper + UI wiring
- Verify any change affecting auth, scheduler, or storage paths with focused tests/manual API calls.

## Common Starting Commands

```bash
rg --files backend/app
rg --files frontend/src
rg -n "include_router|APIRouter" backend/app
rg -n "connector|verify" backend/app/connectors frontend/src
```
