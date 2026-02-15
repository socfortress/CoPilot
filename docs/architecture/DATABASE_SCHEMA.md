# Database Schema (AI Agent-Oriented)

This document summarizes the **current schema** for AI-agent workflows, using **Alembic migrations as source of truth** in `backend/alembic/versions/*.py`.

- Current migration head in this repo: `fb51d610b306` (`backend/alembic/versions/fb51d610b306_add_github_audit_tables.py`)
- Base migration: `bdf40d064ed1` (`backend/alembic/versions/bdf40d064ed1_initial_database_migration.py`)

## Practical Domain Map

For typical agent change work, these domains are most relevant:

- Connectors and integration metadata: `connectors*`, `available_*`, `customer_*_connectors*`, `customer_*integrations*`, `integration_*`, `network_connectors_*`, `custom_alert_creation_*`, `monitoring_alerts`, `sigma_queries`, `github_audit_*`
- Auth / users / roles: `user`, `role`, `smtp`, `user_customer_access`, `user_tag_access`, `role_tag_access`
- Incidents (alerts/cases/tags/comments): all `incident_management_*` tables
- Scheduler/job metadata: `scheduled_job_metadata`, `schedulerjob`, `index_snapshot_schedules`
- Agent data store / artifacts / reports: `agent_datastore`, `incident_management_case_datastore`, `incident_management_case_report_template_datastore`, `vulnerability_reports`, `sca_reports`, `agent_vulnerabilities`

## Critical relationship graph

Compact relationship views for incident workflows and access controls.

### Alerts -> assets (with link fields)

```text
incident_management_alert
  id (PK)
    |
    | 1-to-many via incident_management_asset.alert_linked
    v
incident_management_asset
  alert_linked (FK -> incident_management_alert.id)
  alert_context_id (FK -> incident_management_alertcontext.id)
  index_name, index_id (origin pointer into SIEM index document)
```

### Cases ↔ case-alert links ↔ alerts

```text
incident_management_case                      incident_management_alert
  id (PK)                                     id (PK)
     \                                           /
      \                                         /
       +-- incident_management_casealertlink --+
             case_id  (FK -> incident_management_case.id)
             alert_id (FK -> incident_management_alert.id)
             PK(case_id, alert_id)
```

### Tags (alert/tag join)

```text
incident_management_alert                 incident_management_alerttag
  id (PK)                                 id (PK), tag
     \                                      /
      \                                    /
       +-- incident_management_alert_to_tag --+
             alert_id (FK -> incident_management_alert.id)
             tag_id   (FK -> incident_management_alerttag.id)
             PK(alert_id, tag_id)
```

### IoCs (alert/ioc join)

```text
incident_management_alert                  incident_management_ioc
  id (PK)                                  id (PK), value/type/description
     \                                       /
      \                                     /
       +-- incident_management_alert_to_ioc --+
             alert_id (FK -> incident_management_alert.id)
             ioc_id   (FK -> incident_management_ioc.id)
             PK(alert_id, ioc_id)
```

### Comments (alert comments + case comments)

```text
incident_management_comment
  alert_id (FK -> incident_management_alert.id)
  comment, user_name, created_at

incident_management_case_comment
  case_id (FK -> incident_management_case.id)
  comment, user_name, created_at
```

### Case datastore + report template datastore

```text
incident_management_case
  id (PK)
    |
    | 1-to-many via incident_management_case_datastore.case_id
    v
incident_management_case_datastore
  case_id (FK -> incident_management_case.id)
  bucket_name, object_key, file_name, file_hash, upload_time

incident_management_case_report_template_datastore
  (global report templates; no case FK)
  report_template_name, bucket_name, object_key, file_name, file_hash, upload_time
```

### Tag access control and alert visibility

```text
incident_management_tag_access_settings
  enabled, untagged_alert_behavior, default_tag_id (FK -> incident_management_alerttag.id)

user_tag_access (user_id, tag_id)   role_tag_access (role_id, tag_id)
        \                                  /
         +------ allowed tag ids per identity ------+
                           |
incident_management_alert_to_tag (alert_id, tag_id)
                           |
                   incident_management_alert
```

When tag access control is enabled, alert visibility is constrained by the tag IDs reachable through `user_tag_access` and/or `role_tag_access` joined through `incident_management_alert_to_tag`. `incident_management_tag_access_settings` controls whether this filtering is active and what happens for untagged alerts (`untagged_alert_behavior`, optional `default_tag_id` fallback).

**Tag access enforcement location (code pointers)**
- Core tag RBAC logic: `backend/app/incidents/middleware/tag_access.py` (`TagAccessHandler`)
  - `is_tag_rbac_enabled()` (global enable/disable)
  - `build_alert_query_filters()` (computes accessible tags + untagged behavior)
  - `check_alert_tag_access()` / `can_user_access_alert()` (per-alert decision)
- Applied in incident DB query layer:
  - `backend/app/incidents/services/db_operations.py` uses `tag_access_handler.build_alert_query_filters()` to add SQL `exists()` conditions when counting/listing alerts.

### SIEM data origin + query pattern

- Graylog alerting uses the `gl-events` index pattern (for example `gl-events*` in query flows).
- Those Graylog alert documents live in Wazuh indexer storage (OpenSearch-backed).
- Wazuh indexer is the backing SIEM event store across event sources (endpoints, O365 integrations, network connectors, and other ingested streams).
- CoPilot commonly resolves and displays SIEM records by querying Wazuh indexer with `index_name` plus `index_id`.
- Code pointers:
  - `backend/app/connectors/wazuh_indexer/routes/alerts.py`
  - `backend/app/connectors/wazuh_indexer/services/alerts.py`
  - `backend/app/routers/wazuh_indexer.py`
  - `frontend/src/api/endpoints/alerts.ts`

## Table Inventory (Alembic-Derived)

### Customer, Auth, and Core Platform

| Table | PK | Important columns | Foreign keys | Model file(s) |
|---|---|---|---|---|
| `customers` | `id` | `customer_code`, `customer_name`, contact/address fields, `created_at` | None | `backend/app/db/universal_models.py` (`Customers`) |
| `customersmeta` | `id` | `customer_code`, Graylog/Grafana/Wazuh metadata, `customer_meta_portainer_stack_id` | `customer_code -> customers.customer_code` | `backend/app/db/universal_models.py` (`CustomersMeta`) |
| `customer_provisioning_default_settings` | `id` | `cluster_name`, `cluster_key`, `master_ip`, `grafana_url`, `wazuh_worker_hostname` | None | `backend/app/customer_provisioning/models/default_settings.py` |
| `user` | `id` | `username`, `password`, `email`, `created_at`, `role_id` | `role_id -> role.id` | `backend/app/auth/models/users.py` (`User`) |
| `role` | `id` | `name`, `description` | None | `backend/app/auth/models/users.py` (`Role`) |
| `smtp` | `id` | `email`, `smtp_server`, `smtp_port`, `user_id` | `user_id -> user.id` | `backend/app/auth/models/users.py` (`SMTP`) |
| `user_customer_access` | `id` | `user_id`, `customer_code`, `created_at` | `user_id -> user.id`, `customer_code -> customers.customer_code` | `backend/app/auth/models/users.py` |
| `user_tag_access` | `id` | `user_id`, `tag_id`, `created_at` | `user_id -> user.id`, `tag_id -> incident_management_alerttag.id` | `backend/app/auth/models/users.py` |
| `role_tag_access` | `id` | `role_id`, `tag_id`, `created_at` | `role_id -> role.id`, `tag_id -> incident_management_alerttag.id` | `backend/app/auth/models/users.py` |
| `license` | `id` | `license_key`, customer/company identity fields | None | `backend/app/db/universal_models.py` (`License`) |
| `license_cache` | `id` | `license_key`, `feature_name`, `is_enabled`, `cached_at`, `expires_at`, `license_data` | None | `backend/app/db/universal_models.py` (`LicenseCache`) |
| `log_entries` | `id` | `timestamp`, `event_type`, `user_id`, `route`, `status_code`, `message` | None | `backend/app/db/universal_models.py` (`LogEntry`) |
| `customer_portal_settings` | `id` | `title`, `logo_base64`, `logo_mime_type`, `updated_at`, `updated_by` | None | `backend/app/db/universal_models.py` (`CustomerPortalSettings`) |

### Agents, Vulnerability, and Artifact/Data Store

| Table | PK | Important columns | Foreign keys | Model file(s) |
|---|---|---|---|---|
| `agents` | `id` | `agent_id`, host/OS/status fields, `velociraptor_*`, `customer_code`, `quarantined`, `velociraptor_org` | `customer_code -> customers.customer_code` | `backend/app/db/universal_models.py` (`Agents`) |
| `agent_datastore` | `id` | `agent_id`, `velociraptor_id`, `artifact_name`, `flow_id`, storage columns (`bucket_name`,`object_key`,`file_name`), `file_hash`, `status` | `agent_id -> agents.agent_id` | `backend/app/db/universal_models.py` (`AgentDataStore`) |
| `agent_vulnerabilities` | `id` | `cve_id`, `severity`, `title`, `status`, `discovered_at`, `agent_id`, `customer_code` | `agent_id -> agents.agent_id`, `customer_code -> customers.customer_code` | `backend/app/db/universal_models.py` (`AgentVulnerabilities`) |
| `vulnerability_reports` | `id` | `report_name`, `customer_code`, storage columns, `generated_at`, vulnerability counters, `status` | `customer_code -> customers.customer_code` | `backend/app/db/universal_models.py` (`VulnerabilityReport`) |
| `sca_reports` | `id` | `report_name`, `customer_code`, storage columns, `generated_at`, SCA counters, `status` | `customer_code -> customers.customer_code` | `backend/app/db/universal_models.py` (`SCAReport`) |

### Scheduler and Job Metadata

| Table | PK | Important columns | Foreign keys | Model file(s) |
|---|---|---|---|---|
| `scheduled_job_metadata` | `id` | `job_id`, `last_success`, `time_interval`, `extra_data`, `enabled`, `job_description` | None | `backend/app/schedulers/models/scheduler.py` (`JobMetadata`) |
| `schedulerjob` | `id` | `next_run_time`, `job_state` | None | `backend/app/db/universal_models.py` (`SchedulerJob`) |
| `index_snapshot_schedules` | `id` | schedule metadata (`name`, `index_pattern`, `repository`), retention/last execution fields | None | `backend/app/connectors/wazuh_indexer/models/snapshot_and_restore.py` |

### Connectors and Integrations

| Table | PK | Important columns | Foreign keys | Model file(s) |
|---|---|---|---|---|
| `connectors` | `id` | connector identity/endpoint/auth fields, capability flags, `connector_enabled` | None | `backend/app/connectors/models.py` (`Connectors`) |
| `connectorhistory` | `id` | `connector_id`, `change_timestamp`, `change_description` | `connector_id -> connectors.id` | `backend/app/connectors/models.py` (`ConnectorHistory`) |
| `available_integrations` | `id` | `integration_name`, `description`, `integration_details` | None | `backend/app/integrations/models/customer_integration_settings.py` |
| `available_integrations_auth_keys` | `id` | `integration_id`, `integration_name`, `auth_key_name` | `integration_id -> available_integrations.id` | `backend/app/integrations/models/customer_integration_settings.py` |
| `customer_integrations` | `id` | `customer_code`, `integration_service_id`, `integration_service_name`, `deployed` | None | `backend/app/integrations/models/customer_integration_settings.py` |
| `integration_services` | `id` | `service_name`, `auth_type` | None | `backend/app/integrations/models/customer_integration_settings.py` |
| `integration_subscriptions` | `id` | `customer_id`, `integration_service_id` | `customer_id -> customer_integrations.id`, `integration_service_id -> integration_services.id` | `backend/app/integrations/models/customer_integration_settings.py` |
| `integration_configs` | `id` | `integration_service_id`, `config_key`, `config_value` | `integration_service_id -> integration_services.id` | `backend/app/integrations/models/customer_integration_settings.py` |
| `integration_auth_keys` | `id` | `subscription_id`, `auth_key_name`, `auth_value` | `subscription_id -> integration_subscriptions.id` | `backend/app/integrations/models/customer_integration_settings.py` |
| `customer_integrations_meta` | `id` | Graylog/Grafana metadata (`graylog_*`, `grafana_*`, `grafana_datasource_uid`) | None | `backend/app/integrations/models/customer_integration_settings.py` |
| `available_network_connectors` | `id` | `network_connector_name`, `description`, `network_connector_details` | None | `backend/app/network_connectors/models/network_connectors.py` |
| `available_network_connectors_keys` | `id` | `network_connector_id`, `network_connector_name`, `auth_key_name` | `network_connector_id -> available_network_connectors.id` | `backend/app/network_connectors/models/network_connectors.py` |
| `customer_network_connectors` | `id` | `customer_code`, `network_connector_service_id`, `network_connector_service_name`, `deployed` | None | `backend/app/network_connectors/models/network_connectors.py` |
| `network_connectors_services` | `id` | `service_name`, `auth_type` | None | `backend/app/network_connectors/models/network_connectors.py` |
| `network_connectors_subscriptions` | `id` | `customer_id`, `network_connectors_service_id` | `customer_id -> customer_network_connectors.id`, `network_connectors_service_id -> network_connectors_services.id` | `backend/app/network_connectors/models/network_connectors.py` |
| `network_connectors_configs` | `id` | `network_connector_service_id`, `config_key`, `config_value` | `network_connector_service_id -> network_connectors_services.id` | `backend/app/network_connectors/models/network_connectors.py` |
| `network_connectors_keys` | `id` | `subscription_id`, `auth_key_name`, `auth_value` | `subscription_id -> network_connectors_subscriptions.id` | `backend/app/network_connectors/models/network_connectors.py` |
| `customer_network_connectors_meta` | `id` | Graylog/Grafana connector metadata (`graylog_*`, `grafana_*`, `grafana_datasource_uid`) | None | `backend/app/network_connectors/models/network_connectors.py` |
| `custom_alert_creation_settings` | `id` | customer-wide alert-creation settings, `nvd_url`, custom integration URLs | None | `backend/app/integrations/alert_creation_settings/models/alert_creation_settings.py` |
| `custom_alert_creation_event_order` | `id` | `alert_creation_settings_id`, `order_label` | `alert_creation_settings_id -> custom_alert_creation_settings.id` | `backend/app/integrations/alert_creation_settings/models/alert_creation_settings.py` |
| `custom_alert_creation_condition` | `id` | `event_order_id`, `field_name`, `field_value` | `event_order_id -> custom_alert_creation_event_order.id` | `backend/app/integrations/alert_creation_settings/models/alert_creation_settings.py` |
| `custom_alert_creation_event_config` | `id` | `event_order_id`, `event_id`, `field`, `value` | `event_order_id -> custom_alert_creation_event_order.id` | `backend/app/integrations/alert_creation_settings/models/alert_creation_settings.py` |
| `monitoring_alerts` | `id` | `alert_id`, `alert_index`, `customer_code`, `alert_source` | None | `backend/app/integrations/monitoring_alert/models/monitoring_alert.py` |
| `sigma_queries` | `id` | `rule_name`, `rule_query`, `active`, `time_interval`, execution timestamps | None | `backend/app/connectors/wazuh_indexer/models/sigma.py` |

### Incident Management (Alerts, Cases, Tags, Comments)

| Table | PK | Important columns | Foreign keys | Model file(s) |
|---|---|---|---|---|
| `incident_management_alert` | `id` | `alert_name`, `alert_description`, `status`, `alert_creation_time`, `customer_code`, `source`, `assigned_to`, `escalated` | None | `backend/app/incidents/models.py` (`Alert`) |
| `incident_management_alertcontext` | `id` | `source`, `context` (JSON) | None | `backend/app/incidents/models.py` (`AlertContext`) |
| `incident_management_asset` | `id` | `alert_linked`, `asset_name`, `alert_context_id`, `agent_id`, `customer_code`, `index_name`, `index_id` | `alert_linked -> incident_management_alert.id`, `alert_context_id -> incident_management_alertcontext.id` | `backend/app/incidents/models.py` (`Asset`) |
| `incident_management_comment` | `id` | `alert_id`, `comment`, `user_name`, `created_at` | `alert_id -> incident_management_alert.id` | `backend/app/incidents/models.py` (`Comment`) |
| `incident_management_case` | `id` | `case_name`, `case_description`, `case_creation_time`, `case_status`, `case_closed_time`, `assigned_to`, `customer_code`, `notification_invoked_number`, `escalated` | None | `backend/app/incidents/models.py` (`Case`) |
| `incident_management_casealertlink` | composite: (`case_id`, `alert_id`) | link table case↔alert | `case_id -> incident_management_case.id`, `alert_id -> incident_management_alert.id` | `backend/app/incidents/models.py` (`CaseAlertLink`) |
| `incident_management_case_comment` | `id` | `case_id`, `comment`, `user_name`, `created_at` | `case_id -> incident_management_case.id` | `backend/app/incidents/models.py` (`CaseComment`) |
| `incident_management_alerttag` | `id` | `tag` | None | `backend/app/incidents/models.py` (`AlertTag`) |
| `incident_management_alert_to_tag` | composite: (`alert_id`, `tag_id`) | link table alert↔tag | `alert_id -> incident_management_alert.id`, `tag_id -> incident_management_alerttag.id` | `backend/app/incidents/models.py` (`AlertToTag`) |
| `incident_management_ioc` | `id` | `value`, `type`, `description` | None | `backend/app/incidents/models.py` (`IoC`) |
| `incident_management_alert_to_ioc` | composite: (`alert_id`, `ioc_id`) | link table alert↔IoC | `alert_id -> incident_management_alert.id`, `ioc_id -> incident_management_ioc.id` | `backend/app/incidents/models.py` (`AlertToIoC`) |
| `incident_management_fieldname` | `id` | `source`, `field_name` | None | `backend/app/incidents/models.py` (`FieldName`) |
| `incident_management_assetfieldname` | `id` | `source`, `field_name` | None | `backend/app/incidents/models.py` (`AssetFieldName`) |
| `incident_management_timestampfieldname` | `id` | `source`, `field_name` | None | `backend/app/incidents/models.py` (`TimestampFieldName`) |
| `incident_management_alerttitlefieldname` | `id` | `source`, `field_name` | None | `backend/app/incidents/models.py` (`AlertTitleFieldName`) |
| `incident_management_iocfieldname` | `id` | `source`, `field_name` | None | `backend/app/incidents/models.py` (`IoCFieldName`) |
| `incident_management_customercodefieldname` | `id` | `source`, `field_name` | None | `backend/app/incidents/models.py` (`CustomerCodeFieldName`) |
| `incident_management_notification` | `id` | `customer_code`, `shuffle_workflow_id`, `enabled` | None | `backend/app/incidents/models.py` (`Notification`) |
| `incident_management_case_datastore` | `id` | `case_id`, storage fields (`bucket_name`,`object_key`,`file_name`), `upload_time`, `file_hash` | `case_id -> incident_management_case.id` | `backend/app/incidents/models.py` (`CaseDataStore`) |
| `incident_management_case_report_template_datastore` | `id` | `report_template_name`, storage fields, `upload_time`, `file_hash` | None | `backend/app/incidents/models.py` (`CaseReportTemplateDataStore`) |
| `incident_management_tag_access_settings` | `id` | `enabled`, `untagged_alert_behavior`, `default_tag_id`, `updated_at`, `updated_by` | `default_tag_id -> incident_management_alerttag.id` | `backend/app/incidents/models.py` (`TagAccessSettings`) |
| `incident_management_velo_sigma_exclusion` | `id` | `name`, `field_matches` (JSON), `channel`, `title`, `customer_code`, `created_by`, `enabled` | None | `backend/app/incidents/models.py` (`VeloSigmaExclusion`) |

### GitHub Audit (Added at Head)

| Table | PK | Important columns | Foreign keys | Model file(s) |
|---|---|---|---|---|
| `github_audit_config` | `id` | customer/org token/configuration, filters (JSON), notification and score threshold fields | None | `backend/app/integrations/github_audit/model.py` |
| `github_audit_check_exclusion` | `id` | `config_id`, `customer_code`, check/resource selectors, approval/expiry, `enabled` | `config_id -> github_audit_config.id` | `backend/app/integrations/github_audit/model.py` |
| `github_audit_report` | `id` | `config_id`, organization/report metadata, summary counts, `status`, report JSON blobs | `config_id -> github_audit_config.id` | `backend/app/integrations/github_audit/model.py` |
| `github_audit_baseline` | `id` | `config_id`, `customer_code`, baseline definition, expected checks (JSON), `baseline_report_id`, `is_active` | `config_id -> github_audit_config.id`, `baseline_report_id -> github_audit_report.id` | `backend/app/integrations/github_audit/model.py` |

## Quick Model Scan: Tables Not Obvious From Alembic

The following SQLModel tables are defined in code but do **not** appear in `backend/alembic/versions/*.py` migrations. Treat them as drift candidates / runtime-created tables unless there is an out-of-band migration process.

| Table (in SQLModel) | Model file |
|---|---|
| `sublimealerts` | `backend/app/connectors/sublime/models/alerts.py` (`SublimeAlerts`) |
| `flaggedrule` | `backend/app/connectors/sublime/models/alerts.py` (`FlaggedRule`) |
| `mailbox` | `backend/app/connectors/sublime/models/alerts.py` (`Mailbox`) |
| `triggeredaction` | `backend/app/connectors/sublime/models/alerts.py` (`TriggeredAction`) |
| `sender` | `backend/app/connectors/sublime/models/alerts.py` (`Sender`) |
| `recipient` | `backend/app/connectors/sublime/models/alerts.py` (`Recipient`) |
| `disabledrule` | `backend/app/connectors/wazuh_manager/models/rules.py` (`DisabledRule`) |
| `sap_siem_multiple_logins` | `backend/app/integrations/sap_siem/models/sap_siem.py` (`SapSiemMultipleLogins`) |

## Where To Change Schema

### Source of truth locations

- Alembic migrations: `backend/alembic/versions/`
- Alembic env/config: `backend/alembic/env.py`
- SQLModel definitions commonly touched:
  - `backend/app/db/universal_models.py`
  - `backend/app/incidents/models.py`
  - `backend/app/auth/models/users.py`
  - `backend/app/network_connectors/models/network_connectors.py`
  - `backend/app/integrations/models/customer_integration_settings.py`

### Practical workflow

1. Update or add SQLModel fields/classes in the relevant model file.
2. Generate a migration under `backend/alembic/versions/` (or author manually if needed).
3. Review migration `upgrade()` and `downgrade()` carefully (FK names, nullable transitions, indexes).
4. Apply migration locally and run tests.
5. Update this document if table shape/ownership changes.

### Notes for agent changes

- Prefer extending existing domain tables over creating parallel tables when possible (especially incidents and connector metadata).
- For incident workflows, changes usually involve: `incident_management_alert`, `incident_management_case`, link tables (`*_to_*`), and optional datastore tables.
- For connector onboarding, changes usually involve: `available_*`, `customer_*`, `*_services`, `*_subscriptions`, `*_configs`, `*_keys`, and `*_meta` tables.
- For scheduler automation, coordinate changes between `scheduled_job_metadata`, `schedulerjob`, and domain-specific tables storing job outcomes.
