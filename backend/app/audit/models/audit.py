"""SQLModel table + action vocabulary for the SOC analyst audit log (issue #943).

This is a purpose-built, action-oriented audit trail — distinct from `log_entries`
(`app/db/universal_models.py:LogEntry`), which is an HTTP error log. The audit log records
*who did what, to which entity, when, and with what result*, with optional before/after
values, so the platform can answer accountability/compliance questions.

Design notes:
- `actor_user_id` is deliberately NOT a foreign key, and `actor_username` / `customer_code`
  are denormalized snapshots. An audit record must survive deletion or rename of the user
  or customer it references — a hard FK with cascade would erase history (the opposite of
  what an audit log is for).
- `old_value` / `new_value` are JSON so an action can capture a structured before/after
  (e.g. {"role_id": 2} -> {"role_id": 1}).
- The table is intended to be append-only. Do not expose a general-purpose purge/edit path
  on it (see the implementation plan); retention should be policy-driven, not ad hoc.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON
from sqlalchemy import Column
from sqlmodel import Field
from sqlmodel import SQLModel


class AuditAction(str, Enum):
    """Canonical action identifiers, namespaced as `<domain>.<verb>`.

    Phase 1 covers authentication, user/role management, connectors, agents, response
    actions, cases and the file data store. Add new members here as coverage grows — the
    value is the stable string persisted to the `action` column.
    """

    # Authentication
    AUTH_LOGIN = "auth.login"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_LOGOUT = "auth.logout"

    # Users / RBAC
    USER_CREATE = "user.create"
    USER_DELETE = "user.delete"
    USER_UPDATE = "user.update"
    USER_ROLE_CHANGE = "user.role_change"
    # An admin chose a user's password (temporary, reset or new account), and the user's own
    # change that replaces it (#1277)
    USER_PASSWORD_CHANGE_REQUIRED = "user.password_change_required"
    USER_PASSWORD_CHANGE = "user.password_change"
    # An account disabled or enabled again, by a SOC admin or a customer admin (#1296)
    USER_DISABLE = "user.disable"
    USER_ENABLE = "user.enable"
    # A SOC admin makes a portal user an administrator of one of their customers, or not (#1296)
    CUSTOMER_ADMIN_UPDATE = "customer_admin.update"
    # What a customer admin does to their customer's portal users from the portal (#1296)
    CUSTOMER_USER_INVITE = "customer_user.invite"
    CUSTOMER_USER_TOTP_RESET = "customer_user.totp_reset"
    CUSTOMER_USER_PASSWORD_RESET = "customer_user.password_reset"
    # A portal user made read-only on one of their customers, or allowed to change data again,
    # by a SOC admin or a customer admin (#1312)
    CUSTOMER_USER_READ_ONLY_UPDATE = "customer_user.read_only_update"
    # A user's own two-factor authentication, set up or turned off from their profile (#1298)
    USER_TOTP_ENABLE = "user.totp_enable"
    USER_TOTP_DISABLE = "user.totp_disable"

    # Connectors
    CONNECTOR_CREATE = "connector.create"
    CONNECTOR_UPDATE = "connector.update"
    CONNECTOR_DELETE = "connector.delete"

    # Agents / assets
    AGENT_DELETE = "agent.delete"
    AGENT_CRITICALITY_CHANGE = "agent.criticality_change"

    # Velociraptor response actions
    RESPONSE_QUARANTINE = "response.quarantine"
    RESPONSE_COMMAND_EXECUTE = "response.command_execute"
    ARTIFACT_COLLECT = "artifact.collect"
    COPILOT_ACTION_INVOKE = "response.copilot_action_invoke"
    SYSMON_CONFIG_DEPLOY = "response.sysmon_deploy"

    # Cases
    CASE_CREATE = "case.create"
    # Status changes and comments on alerts and cases, by the SOC or a portal user, so a customer's
    # audit log answers who closed what and who said what (#1298). A comment's text is never stored.
    CASE_STATUS_CHANGE = "case.status_change"
    CASE_COMMENT_CREATE = "case.comment_create"
    CASE_COMMENT_EDIT = "case.comment_edit"
    CASE_COMMENT_DELETE = "case.comment_delete"

    # Alert triage
    ALERT_VERDICT_SET = "alert.verdict_set"
    ALERT_VERDICT_CLEAR = "alert.verdict_clear"
    ALERT_STATUS_CHANGE = "alert.status_change"
    ALERT_COMMENT_CREATE = "alert.comment_create"
    ALERT_COMMENT_EDIT = "alert.comment_edit"
    ALERT_COMMENT_DELETE = "alert.comment_delete"

    # Customer PDF reports: generated, downloaded and deleted (#1298)
    REPORT_GENERATE = "report.generate"
    REPORT_DOWNLOAD = "report.download"
    REPORT_DELETE = "report.delete"

    # AI Analyst from the Customer Portal (#1215)
    AI_ANALYSIS_REQUEST = "ai_analysis.request"
    AI_REPORT_SETTINGS_UPDATE = "ai_report.settings_update"
    # The Customer Portal's Activity page switch, per customer (#1284).
    ACTIVITY_SETTINGS_UPDATE = "activity.settings_update"
    # The Customer Portal's Exposure page switch, per customer (#1289).
    EXPOSURE_SETTINGS_UPDATE = "exposure.settings_update"
    # The languages a customer's portal users may pick (#1310).
    PORTAL_LANGUAGES_SETTINGS_UPDATE = "portal_languages.settings_update"
    # The Customer Portal's Audit Log page switch, per customer (#1298).
    AUDIT_SETTINGS_UPDATE = "audit.settings_update"
    # "Ask the SOC" from the Customer Portal (#1305): a portal user's question (refusals as
    # failures), the SOC marking one answered by hand, and the per-customer switch.
    SOC_REQUEST_CREATE = "soc_request.create"
    SOC_REQUEST_ANSWER = "soc_request.answer"
    SOC_REQUEST_SETTINGS_UPDATE = "soc_request.settings_update"
    # Threat Intel enrichment of IOCs in the Customer Portal (#1318): a lookup that reached
    # VirusTotal or OpenCTI (failure when no source answered), and the per-customer switch.
    IOC_ENRICHMENT_LOOKUP = "ioc_enrichment.lookup"
    IOC_ENRICHMENT_SETTINGS_UPDATE = "ioc_enrichment.settings_update"

    # Talon v2 chat action proposals, decided and run in CoPilot (talon-analyst M5-11). A
    # quarantine run this way also records RESPONSE_QUARANTINE, from its own route.
    TALON_ACTION_APPROVE = "talon_action.approve"
    TALON_ACTION_DENY = "talon_action.deny"
    TALON_ACTION_EXECUTE = "talon_action.execute"
    # An admin's per-customer Talon budget override (talon-analyst M5-9a, FR-COST-4), with the old
    # and new ceilings; refused attempts are recorded as failures.
    TALON_BUDGET_UPDATE = "talon_budget.update"
    # The per-customer automation policy and the global automation switch (talon-analyst AP-2,
    # D85), with the old and new values (raising level 3 or 4: the admin's risk acknowledgement);
    # and each automated start the Talon service account was given a slot for, recorded in the
    # same transaction as its talon_automation_start row, before the flow starts.
    TALON_AUTOMATION_POLICY_UPDATE = "talon_automation.policy_update"
    TALON_AUTOMATION_START = "talon_automation.start"
    # A Talon memory forgotten from the AI Analyst page's Memory tab: a customer's one-off review
    # lesson or chat `remember` lesson, or one of the caller's own chat memories. Refusals (by
    # CoPilot or by talon-analyst) are recorded as failures.
    TALON_MEMORY_FORGET = "talon_memory.forget"
    # An ops finding acknowledged, muted or reopened, or an ops job run now, from the AI Analyst
    # page's Ops tab (talon-analyst D96, plan OJ-5). Every request sent to talon-analyst is recorded;
    # its refusals as failures, no answer as unknown.
    TALON_OPS_ACKNOWLEDGE = "talon_ops.acknowledge"
    TALON_OPS_MUTE = "talon_ops.mute"
    TALON_OPS_REOPEN = "talon_ops.reopen"
    TALON_OPS_RUN = "talon_ops.run"
    # The per-customer Talon portal chat settings (talon-analyst D97, PC-3): an admin's change, or
    # the chat turned off because the customer's AI reports were, with the old and new values.
    TALON_PORTAL_CHAT_UPDATE = "talon_portal_chat.update"

    # SOCFortress UBA per customer (#1241)
    UBA_MODE_CHANGE = "uba.mode_change"
    UBA_ROLLBACK = "uba.rollback"

    # File data store
    DATASTORE_FILE_CREATE = "datastore.file_create"
    DATASTORE_FILE_DELETE = "datastore.file_delete"


class AuditResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    # The action was asked for and no answer came back: it may or may not have happened (a Talon
    # memory forget that timed out).
    UNKNOWN = "unknown"


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Actor — snapshot, no FK (record must outlive the user).
    actor_user_id: Optional[int] = Field(default=None, index=True)
    actor_username: Optional[str] = Field(default=None, max_length=256, index=True)

    # Tenant — string snapshot, no FK (record must outlive the customer).
    customer_code: Optional[str] = Field(default=None, max_length=50, index=True)

    # What happened.
    action: str = Field(max_length=128, index=True)
    entity_type: Optional[str] = Field(default=None, max_length=128, index=True)
    entity_id: Optional[str] = Field(default=None, max_length=256)
    result: str = Field(default=AuditResult.SUCCESS.value, max_length=32, index=True)

    # Optional structured before/after and context.
    old_value: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    new_value: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    source_ip: Optional[str] = Field(default=None, max_length=64)
    details: Optional[str] = Field(default=None, max_length=5024)
