# Features by Area

This page is intended to make “hidden” features discoverable.

## Incident Management (operators)

![Incident Alerts](../assets/ui/incident-alerts.png)

- Alerts: triage, tagging, assignment, escalation
- Cases: create, link alerts, close lifecycle
- Comments: alert comments and case comments
- IoCs: attach IoCs to alerts
- Artifacts / datastores: case evidence files and report templates

## SIEM / Data (operators + engineers)
- Wazuh Indexer search-backed views (CoPilot often pivots using `index_name` + `index_id`)
- Graylog alerting events (commonly `gl-events*`)

## Integrations / Connectors (engineers)

![Connectors](../assets/ui/connectors.png)

- Connectors: configure and verify tool connectivity
- Network connectors: customer-scoped connector configs/keys
- Integration settings: customer integration configuration

## Reporting

![Report Creation](../assets/ui/report-general.png)

- Grafana reporting and PDF generation
- Case report templates

## Automation

![Scheduler](../assets/ui/scheduler.png)

- Scheduler jobs (collectors, sync, alert creation)
- Active response (where enabled)
