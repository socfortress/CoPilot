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
| `user.disable` / `user.enable` | SOC Security tab or a customer admin in the portal (#1296) | `user` / username | details say who; + customer_code from the portal |
| `customer_admin.update` | SOC Security tab (#1296) | `user` / username | old/new = {is_customer_admin}; + customer_code |
| `customer_user.invite` | a customer admin in the portal (#1296) | `user` / username | new = {username, email, customer_codes}; + customer_code |
| `customer_user.totp_reset` / `customer_user.password_reset` | a customer admin in the portal (#1296) | `user` / username | + customer_code; the password is never recorded |
| `user.totp_enable` / `user.totp_disable` | a user's own 2FA from their profile, `app/auth/routes/totp.py` (#1298) | `user` / username | + source_ip |
| `alert.status_change` / `case.status_change` | the incidents routes, single and bulk (#1298) | `alert`/`case` / id | old/new = {status}; + customer_code; one row per item that moved |
| `alert.comment_create/edit/delete` / `case.comment_*` | the incidents comment routes (#1298) | `alert`/`case` / id | new = {comment_id}; + customer_code; **never the comment's text** |
| `case.create` (from an alert) | `POST /incidents/db_operations/case/from-alert` (#1298) | `case` / case_id | new = {case_name, customer_code, alert_id} |
| `report.generate/download/delete` | `app/incidents/routes/customer_report.py` (#1298) | `report` / report_id | new = {report_name, date_from, date_to}; + customer_code |
| `audit.settings_update` | the portal Audit Log switch, `PUT /customer_portal/audit/settings/{code}` (#1298) | `customer_portal_audit_settings` / code | old/new = {enabled} |
| `customer_user.read_only_update` | a portal user made read-only on a customer, or allowed changes again, by a SOC admin (`PUT /auth/security/customers/{code}/users/{id}/read-only`) or a customer admin (`PUT /customer_portal/users/{id}/read-only`) (#1312), only when it changes | `user` / username | old/new = {read_only}; details say who (SOC or customer admin) |
| `portal_languages.settings_update` | the languages a customer's portal users may pick, `PUT /customer_portal/languages/settings/{code}` (#1310), only when the set changes | `customer_portal_language_settings` / code | old/new = {languages} |
| `soc_request.create` | a portal user asks the SOC about an alert or a case (#1305) | `case` or `alert` / its id | new = {request_id, urgency, origin_alert_id}; refusals (switched off, cooldown, daily limit, comment not written) as failures with the reason in details; never the question |
| `soc_request.answer` | an analyst marks a customer question answered by hand (#1305) | `soc_request` / id | new = {status, via: manual}; answering by a SOC comment is not audited apart (the comment is) |
| `soc_request.settings_update` | Customers → customer → Ask the SOC (#1305), when it changes | `customer_portal_soc_request_settings` / customer_code | old/new = {enabled, daily_request_limit} |
| `ioc_enrichment.lookup` | a portal user checks an IOC of their alert against VirusTotal / OpenCTI and at least one source is asked (#1318) | `ioc` / its id | new = {alert_id, value, sources: {source: status}}; failure when no source answered (nothing cached, nothing counted); a result served from the cache is not audited |
| `ioc_enrichment.settings_update` | Customers → customer → IOC Enrichment (#1318), when it changes | `customer_portal_ioc_enrichment_settings` / customer_code | old/new = {enabled, daily_lookup_limit} |
| `talon_portal_chat.update` | Customers → customer → AI Report → Talon chat in the portal (talon-analyst D97), every admin write; and the chat turned off because the customer's AI reports were (details say so) | `customer_portal_chat_settings` / customer_code | old/new = {portal_chat_enabled, log_search_enabled, daily_message_limit, user_daily_message_limit, version} |
| `connector.create/update/delete` | `app/connectors` services | `connector` / name | new/old = sanitized config (no secrets) |
| `agent.delete` | `app/agents/routes/agents.py` delete | `agent` / agent_id | + customer_code |
| `agent.criticality_change` | asset critical/non-critical toggle | `agent`/`asset` / id | old/new = {critical: bool} |
| `response.quarantine` | `velociraptor/services/artifacts.py:quarantine_host` | `agent` / client_id | details = action (quarantine/remove) |
| `response.command_execute` | `velociraptor/routes/artifacts.py:start_command_as` (`/command`, an approved Talon `endpoint_command`) | `agent` / client_id | details = artifact (NOT raw command) |
| `artifact.collect` | `velociraptor/routes/artifacts.py:start_collection_as` (`/collect`, an approved Talon `collect_artifact`) | `agent` / client_id | new = {artifact_name} |
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
