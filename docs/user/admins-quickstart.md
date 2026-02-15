# Quickstart (Admins / Engineers)

![Connectors](../assets/ui/connectors.png)

## Where you spend most of your time

- **Connectors**: configure connectivity to the toolchain (Wazuh, Graylog, Grafana, Velociraptor, etc.).
- **External Services / Integrations**: configure per-customer integrations.
- **Scheduler**: enable/disable and tune background jobs/collectors.

## Core workflows

### 1) Configure connectors

![Connectors](../assets/ui/connectors.png)

- Add URLs / credentials
- Verify connectivity

### 2) Validate SIEM data availability

![Indices → Index Management](../assets/ui/indices-management.png)

- Confirm Wazuh Indexer is reachable
- Confirm Graylog alerts are being written (often `gl-events*`)

### 3) Provision customer resources (if applicable)

![Customers](../assets/ui/customers.png)

- Use customer provisioning flows for Grafana/Graylog/Wazuh/Portainer where supported

### 4) Operationalize automation

![Scheduler](../assets/ui/scheduler.png)

- Enable scheduled collectors
- Confirm job metadata updates and error handling
