# Audit Log (SOC analyst activity tracking)

Tracks issue #943. A purpose-built, **action-oriented** audit trail: *who did what, to which
entity, when, with what result*, plus optional before/after values.

This is intentionally **separate from `log_entries`** (`app/db/universal_models.py:LogEntry`),
which is an HTTP **error** log written by the exception handlers. The two solve different
problems; do not conflate them. (We are deliberately leaving the disabled per-request
access-logging middleware alone — it is HTTP-shaped and noisy, the wrong tool for an audit
log.)

## Module layout

```
app/audit/
  models/audit.py     # AuditLog table + AuditAction / AuditResult enums
  services/audit.py   # record_audit_event(...) — the single write entry point
  schema/audit.py     # Pydantic read shapes (consumed by the Phase 2 read API)
```

The model is registered in `alembic/env.py` so autogenerate sees it.

## Schema (`audit_log`)

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `timestamp` | datetime (UTC), indexed | set on insert |
| `actor_user_id` | int, nullable, indexed | **no FK** — record must outlive the user |
| `actor_username` | str(256), nullable, indexed | denormalized snapshot |
| `customer_code` | str(50), nullable, indexed | **string, no FK** — must outlive the customer |
| `action` | str(128), indexed | `<domain>.<verb>`, e.g. `agent.delete` |
| `entity_type` | str(128), nullable, indexed | e.g. `agent`, `user`, `connector` |
| `entity_id` | str(256), nullable | string to fit int/uuid/name ids |
| `result` | str(32), indexed | `success` \| `failure` |
| `old_value` | JSON, nullable | structured before-state |
| `new_value` | JSON, nullable | structured after-state |
| `source_ip` | str(64), nullable | from `X-Forwarded-For` / client |
| `details` | str(5024), nullable | freeform context |

**Append-only by intent.** Do not add a general purge/edit endpoint on this table; retention
must be policy-driven. (Contrast with `log_entries`, which *does* expose admin purge.) Confirm
the retention requirement against the relevant compliance framework before Phase 2 ships any
delete path.

## Write path — `record_audit_event(...)`

Call it from a route/service **after** the action has committed (or on failure, with
`result=AuditResult.FAILURE`). It writes in its **own** short-lived session, so an
audit-write failure can neither roll back nor 500 the business action, and it never raises
(best-effort: failures are logged and swallowed).

```python
from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event

await record_audit_event(
    action=AuditAction.AGENT_DELETE,
    actor_user_id=current_user.id,
    actor_username=current_user.username,
    customer_code=agent.customer_code,
    entity_type="agent",
    entity_id=agent_id,
    request=request,            # source_ip extracted automatically
)
```

The actor must come from the **validated** `current_user` dependency — never from a raw
token decode (the `decode_token` sentinel-string path can yield a non-authenticated
"username"; see GHSA-c6jc-rh4j-wg88 follow-up).

## Phase 1 instrumentation map

Wire `record_audit_event` at these mutating call sites once the table exists. Each row =
one instrumentation point.

| Action | Where (route/service) | entity_type / id | old→new / details |
|---|---|---|---|
| `auth.login` | `app/auth/routes/auth.py` token issue (success) | `user` / username | + set `user.last_login_at` |
| `auth.login_failed` | same, on bad credentials | `user` / attempted username | details = reason |
| `auth.logout` | logout endpoint **if added** | `user` | JWT is stateless — see note |
| `user.create` | `app/auth` user create | `user` / new id | new = {username, role_id} |
| `user.delete` | `app/auth` user delete | `user` / id | old = {username, role_id} |
| `user.role_change` | `app/auth` role update | `user` / id | old/new = {role_id} |
| `connector.create/update/delete` | `app/connectors` services | `connector` / name | new/old = sanitized config (no secrets) |
| `agent.delete` | `app/agents/routes/agents.py` delete | `agent` / agent_id | + customer_code |
| `agent.criticality_change` | asset critical/non-critical toggle | `agent`/`asset` / id | old/new = {critical: bool} |
| `response.quarantine` | `velociraptor/services/artifacts.py:quarantine_host` | `agent` / client_id | details = action (quarantine/remove) |
| `response.command_execute` | `…artifacts.py:run_remote_command` | `agent` / client_id | details = artifact (NOT raw command) |
| `artifact.collect` | `…artifacts.py:run_artifact_collection` | `agent` / client_id | new = {artifact_name} |
| `case.create` | `app/incidents` case create | `case` / case_id | new = {case_name, customer_code} |
| `datastore.file_create` | `app/data_store` upload | `file` / object_key | + bucket, customer_code |
| `datastore.file_delete` | `app/data_store` delete | `file` / object_key | |

**Login / last-login:** add `last_login_at: Optional[datetime]` to the `User` model, set it on
successful auth, and surface it in the profile/login response (a second, small migration).

**Logout caveat:** sessions are stateless JWTs — there is no server-side session to end, so
`auth.logout` is only meaningful if an explicit logout endpoint (or token denylist) is added.
Scope this expectation with the requester.

**Secrets:** never put credentials/tokens into `old_value`/`new_value`/`details`. For
connector changes, snapshot only non-sensitive fields.

## Phasing

- **Phase 1 (this work):** table + `record_audit_event` + login/last-login + the high-value
  mutations above (auth, user/role, connector, agent delete, quarantine/command/artifact,
  case create, datastore).
- **Phase 2:** admin-only read API (filter by user/action/entity/date/result — reuse the
  existing `Logs.vue` + filter components), richer old/new diffing, SSO/portal/platform
  config-change coverage, and a documented retention policy.
