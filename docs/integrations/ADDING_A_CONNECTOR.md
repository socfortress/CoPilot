# Adding a Connector (AI Agent Checklist)

Use this when introducing a new backend connector integration and wiring it through UI/API.

## Scope

This checklist covers:
- connector bootstrap record
- verify dispatch wiring
- connector utility client + verifier
- route wiring
- frontend endpoint/UI integration

## 1) Add Connector to Seed Data

File: `backend/app/db/db_populate.py`

Actions:
1. Update `get_connectors_list()` with your new connector tuple.
2. Pick exactly one auth mode flag via `accepts_key`:
   - `host_only`
   - `api_key`
   - `username_password`
   - `file`
3. If needed, define `extra_data_key` env var for `connector_extra_data`.
4. Ensure env var naming matches `load_connector_data()` prefix rule:
   - `connector_name.upper().replace("-", "_").replace(" ", "_")`

Result:
- connector appears in `/api/connectors` after startup seed.

## 2) Implement Connector Utility Module

File path (new): `backend/app/connectors/<service>/utils/universal.py`

Minimum functions to provide:
1. `verify_<service>_connection(connector_name: str)`
2. `create_<service>_client(connector_name: str = "<Connector-Display-Name>")`

Implementation requirements:
- Pull credentials via `get_connector_info_from_db` from `backend/app/connectors/utils.py`.
- Return consistent verify payload:
  - `{"connectionSuccessful": bool, "message": str}`
- Raise `HTTPException` for hard failures in runtime client creation.

## 3) Register Verify Dispatch

File: `backend/app/connectors/services.py`

Actions:
1. Import your verifier function.
2. Add service class (pattern: `<ServiceName>Service`) implementing `verify_authentication`.
3. Add mapping in `get_connector_service()` `service_map`:
   - key must match DB `connector_name` exactly.

If omitted, `/api/connectors/verify/{id}` will return unsupported/None behavior.

## 4) Add Connector Routes (If Exposing Feature APIs)

Typical files:
- `backend/app/connectors/<service>/routes/*.py`
- `backend/app/connectors/<service>/services/*.py`
- `backend/app/connectors/<service>/schema/*.py`

Router wiring:
1. Add/modify router module `backend/app/routers/<service>.py`.
2. Include route groups with appropriate prefixes/tags.
3. Add top-level include in `backend/copilot.py`:
   - `from app.routers import <service>`
   - `api_router.include_router(<service>.router)`

Without step 3, routes compile but are unreachable.

## 5) Frontend Endpoint Wiring

Primary files:
- `frontend/src/api/endpoints/connectors.ts`
- optional new endpoint file if connector has dedicated APIs (pattern in `frontend/src/api/endpoints/*.ts`)
- `frontend/src/api/index.ts` (export)

Checklist:
1. Reuse generic `/connectors` endpoints if only configuring/verifying credentials.
2. Add dedicated endpoint wrapper(s) for new connector-specific backend routes.
3. Ensure payload type definitions exist/update in `frontend/src/types/*.d.ts`.

## 6) Frontend UI Wiring

Connector configuration UI already exists:
- View: `frontend/src/views/Connectors.vue`
- List: `frontend/src/components/connectors/ConnectorsList.vue`
- Item: `frontend/src/components/connectors/ConnectorItem.vue`
- Form: `frontend/src/components/connectors/ConfigForm/ConfigForm.vue`

Checklist:
1. Ensure DB flags (`connector_accepts_*`) drive the correct form type.
2. Add connector logo asset if needed (`frontend/public/images/connectors/<lowercase-name>.svg`).
3. Add any connector-specific screens/routes only if required:
   - route map: `frontend/src/router/index.ts`

## 7) Environment + Secrets

Update `.env.example` with required connector vars so bootstrap is deterministic.

Rules:
- Do not hardcode secrets in code.
- Read credentials from DB connector config at runtime.
- Keep placeholder defaults non-production.

## 8) Validation Steps

1. Start stack and call `GET /api/connectors` to confirm seed row exists.
2. Configure connector in UI (`/connectors`).
3. Call `POST /api/connectors/verify/{id}` and check `connectionSuccessful`.
4. Exercise at least one runtime endpoint that uses `create_<service>_client`.

## Common Pitfalls

- TLS verification mismatch:
  - many existing connectors use `verify=False`/`verify_certs=False` for self-signed deployments.
  - if you enable strict TLS, make it explicit and configurable.
- Timeout defaults too low/high:
  - define per-connector timeouts; include retries only when safe.
- Wrong auth header format:
  - token connectors often require exact header names/prefixes (`Authorization: Bearer ...`, custom headers, etc.).
- Connector name mismatch:
  - DB seed name and `service_map` key must be identical.
- Router not included at top level:
  - adding route files alone is insufficient; include in `backend/copilot.py`.
- Missing frontend export/wiring:
  - endpoint file exists but not exported in `frontend/src/api/index.ts`.
