# User Guide Overview

CoPilot is a “single pane of glass” for operating an open-source SOC/SIEM stack.

![CoPilot Overview dashboard](../assets/ui/overview.png)

## Two primary user roles

### SOC operator / analyst
- Works primarily in **Incident Management** (alerts, cases, triage, tagging, comments, artifacts, reporting).
- Consumes events and detections coming from the SIEM data store.

### Admin / engineer
- Configures the systems that produce alerts and the data sources behind them (connectors, integrations, network connectors, scheduler jobs, etc.).
- Responsible for keeping the stack healthy and ensuring the right data is being ingested.

## Mental model

- **Wazuh Indexer (OpenSearch-backed)** is the primary **event datastore** for SIEM events (endpoints, O365 integrations, network connectors, and other sources).
- **Graylog** commonly produces alerts into the `gl-events*` index pattern, which can then be queried and displayed through CoPilot’s Wazuh Indexer integration.
- CoPilot frequently resolves SIEM documents using **`index_name` + `index_id`**.
