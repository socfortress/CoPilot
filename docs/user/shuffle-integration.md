# CoPilot ↔ Shuffle Integration (Admin/Operator)

CoPilot integrates with **Shuffle** so you can attach **automation and external notifications** (Teams/Slack/Jira/Email/VT enrichment, etc.) to alerts and cases **without** SOCFortress having to ship a bespoke integration for every downstream tool.

At a high level:

- **Graylog** creates the *SIEM event/alert* (via Event Definitions)
- **CoPilot** polls Graylog for *new, unprocessed* events and turns them into **CoPilot Alerts/Cases**
- **CoPilot** sends a structured payload to **Shuffle**, which runs a workflow you choose

---

## Why we do it this way

### 1) Scale integrations without bloating CoPilot
CoPilot is the “hub” for the stack, but the long tail of integrations (Teams, Jira, PagerDuty, ServiceNow, custom webhooks, etc.) is endless.

Shuffle is purpose-built for this:

- hundreds of apps/connectors
- easy HTTP/webhook support for anything else
- workflows/playbooks can be owned by the operator team (not necessarily product engineering)

### 2) Keep automation close to your environment (minimize exposure)
Shuffle supports an architecture where the **UI/orchestration can be cloud-hosted** while execution happens via an **on‑prem “location/worker”** inside your network.

That’s valuable for SIEM stacks because you often want to:

- reach internal services (Wazuh Manager, Indexer/OpenSearch, AD, internal APIs)
- avoid poking inbound firewall holes
- keep credentials and execution inside your boundary

### 3) Strong separation of concerns
- **Graylog**: detection logic (queries, thresholds, correlation)
- **CoPilot**: multi-tenant alert/case lifecycle + normalization + UI + API
- **Shuffle**: automation/orchestration + outbound integrations

---

## Data flow (what triggers what)

### Alerts (automatic)
1. A Graylog **Event Definition** triggers.
2. Graylog writes an event into its events index (e.g., `gl-events_*`).
3. CoPilot’s scheduler job **polls** for new events where `copilot_alert_id = none`.
4. CoPilot creates a **CoPilot Alert** and then updates the Graylog event so it won’t be reprocessed.
5. If a Shuffle notification workflow is configured for that customer, CoPilot invokes it and includes:
   - alert/case metadata
   - customer code
   - asset identifier
   - **alert context** (see below)

### Cases (manual trigger)
Cases can be triggered into Shuffle **manually** from the CoPilot UI. This is intentional so case automation isn’t accidentally run without an analyst decision.

---

## What CoPilot sends to Shuffle (payload model)

CoPilot sends a JSON payload that includes:

- **Alert ID / Case ID** (CoPilot identifiers)
- **Customer code** (multi-tenant routing)
- **Asset name** (e.g., Wazuh agent name, O365 mailbox/user, etc.)
- **Alert Context**: a small, curated set of fields you choose per Source

### Alert Context comes from *Sources*
The most important concept for operators/admins:

> **The fields that appear in Shuffle’s `alert_context` are defined by the CoPilot Source configuration.**

That’s why CoPilot can support wildly different log types:

- Wazuh endpoint events → asset might be `agent.name`
- O365 events → asset might be `o365.recipients` or `user_id`

You choose which fields are “headline context” for that Source, and those same fields become the default “automation payload” for Shuffle.

---

## Setup: enabling CoPilot → Shuffle

### Step 1 — Get a Shuffle API key
In Shuffle:

1. Go to **User Account / Settings**
2. Copy the **API key**

### Step 2 — Add the Shuffle API key to CoPilot
In CoPilot:

1. Navigate to **Connectors**
2. Locate **Shuffle**
3. Paste the API key and **verify**

### Step 3 — Create a Shuffle workflow to receive CoPilot notifications
Create a workflow in Shuffle (example: `SIEM Alert — <customer>`). The workflow will receive the CoPilot payload as input.

### Step 4 — Set the notification workflow per customer
In CoPilot:

1. Open the **Customer**
2. Go to **Notification Workflow**
3. Create/configure the notification and set the **Shuffle Workflow ID**

**Result:**
- New alerts for that customer can invoke the workflow automatically
- Cases can invoke the workflow when manually triggered

---

## How this ties back to Graylog + Indexer/OpenSearch

A quick mental model (this matters when debugging):

- **Indexer/OpenSearch (Wazuh Indexer)** stores the actual event data.
- **Graylog** manages streams/index sets and runs event definitions (alerting) by querying the indexer.
- **CoPilot** reads Graylog’s generated events and then enriches/normalizes them into CoPilot alerts.

So when you want to automate enrichment in Shuffle (e.g., look up related events, run searches, pull agent state):

- Query **Indexer/OpenSearch** for raw events/search
- Use **Wazuh Manager API** for agent lifecycle state
- Use **CoPilot API** when you want CoPilot’s normalized view (alerts/cases/customers)

---

## Practical examples (common workflows)

- Post to **Microsoft Teams** when a High severity alert arrives
- Enrich hashes/domains with **VirusTotal** before an analyst sees the alert
- Create a **Jira** ticket with alert context and links back to CoPilot
- Invoke an internal **FastAPI microservice** (e.g., disable AD user) with an approval step

---

## Troubleshooting checklist

1. **Is the Graylog Event Definition firing?**
   - Confirm the event exists in `gl-events_*`.
2. **Is CoPilot creating the alert?**
   - If `copilot_alert_id` remains `none`, CoPilot likely can’t map the event to a Source.
3. **Is the Source configured correctly?**
   - Ensure the Source matches the event’s `syslog_type` and correct field mapping.
4. **Is the Shuffle connector verified in CoPilot?**
5. **Is the customer’s Shuffle Workflow ID set?**
6. **Check Shuffle runs** for the workflow.

---

## Related docs

- [Incident Sources](ui/incident-sources.md)
- [Alerts (SIEM)](ui/alerts-siem.md)
- [Connectors](ui/connectors.md)
- [External Services](ui/external-services.md)
