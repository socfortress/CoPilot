---
title: Graylog Threshold Alerts
description: How to configure Graylog threshold-based event definitions and send them to CoPilot via webhook.
---

# Graylog Threshold Alerts

## Overview

Not all detections are triggered by a single event. Some security-relevant scenarios — such as excessive login failures, brute-force attempts, or repeated policy violations — only become meaningful when a **count of events exceeds a threshold** within a given time window.

Graylog handles these through **threshold-based Event Definitions**, which are fundamentally different from standard (single-event) alerts:

| Alert type | Trigger | Example |
|---|---|---|
| **Standard** | A single matching event | Wazuh rule fires for malware detection |
| **Threshold** | Count of matching events ≥ N in a time window | 10+ failed logins in 5 minutes |

Because threshold alerts aggregate multiple events, there is no single underlying event `_id` to reference. CoPilot therefore exposes a **dedicated webhook endpoint** (`/create/threshold`) that accepts the aggregated alert metadata and converts it into an Incident Management alert.

---

## When to use threshold alerts

Threshold alerts are the right choice when you need to detect:

- **Brute-force / credential stuffing** — e.g., ≥ 10 failed authentication attempts within 5 minutes for the same user or source IP.
- **Excessive privilege escalation attempts** — e.g., ≥ 5 `sudo` failures on a single host in 10 minutes.
- **Anomalous volume** — e.g., ≥ 100 Office 365 `FileDeleted` events from the same user in 15 minutes.
- **Repeated policy violations** — e.g., ≥ 3 DLP policy hits from the same endpoint in 1 hour.
- **Scan / enumeration detection** — e.g., ≥ 50 connection attempts to different ports on the same destination in 1 minute.

> **Rule of thumb:** If the detection logic includes words like *"more than,"* *"at least,"* or *"within X minutes,"* you likely need a threshold alert.

---

## Step-by-step configuration

### 1. Create the Event Definition in Graylog

1. Navigate to **Alerts → Event Definitions** in the Graylog web UI.
2. Click **Create Event Definition**.
3. Fill in the **Title** and **Description** — this title will become the alert name inside CoPilot.

#### Condition Configuration

4. Under **Condition Type**, select **Filter & Aggregation**.
5. Define your **search query** (filter) to match the relevant log events (e.g., `source:office365 AND event_type:login_failure`).
6. Set the **Search within** time window (e.g., `5 minutes`).
7. Set the **Execute search every** interval (e.g., `1 minute`).
8. Under **Aggregation**, configure:
   - **Group By** — the field(s) to group on (e.g., `source_ip`, `username`, `agent_name`).
   - **Condition** — e.g., `count() >= 10`.

> ⚠️ Make sure the aggregation condition accurately reflects the threshold you want. Test with **Preview** before saving.

### 2. Define the required Custom Fields

CoPilot's `/create/threshold` endpoint requires **four custom fields** to be set on the Event Definition. These fields map the Graylog event into a CoPilot alert.

Navigate to the **Fields** tab of the Event Definition and add the following:

| Field name | Type | Required | Description |
|---|---|---|---|
| `CUSTOMER_CODE` | `string` | ✅ | The customer code this alert belongs to (must match a customer in CoPilot). |
| `SOURCE` | `string` | ✅ | The source/integration name (e.g., `office365`, `wazuh`, `custom`). |
| `ALERT_DESCRIPTION` | `string` | ✅ | A human-readable description of what was detected. |
| `ASSET_NAME` | `string` | ✅ | The name of the affected asset (hostname, username, IP — whatever is most relevant). |

For each field, you can either:

- Set a **static value** (e.g., `CUSTOMER_CODE` = `ACME`) if this event definition is customer-specific, or
- Use a **template** that references Graylog event fields (e.g., `ASSET_NAME` = `${source.agent_name}`).

**Example field configuration:**

```
CUSTOMER_CODE  →  ACME
SOURCE         →  office365
ALERT_DESCRIPTION → Excessive login failures detected (threshold: 10 in 5 min)
ASSET_NAME     →  ${source.agent_name}
```

> 🚨 **IMPORTANT:** Do **NOT** add a field called `COPILOT_ALERT_ID` with a value of `NONE`. This will break the auto-alert creation functionality for standard (non-threshold) alerts.

### 3. Create the HTTP Notification

1. Navigate to the **Notifications** tab of your Event Definition (or go to **Alerts → Notifications → Create Notification**).
2. Select **HTTP Notification** as the notification type.

> 🚨 **IMPORTANT:** Use the standard **HTTP Notification** type — do **NOT** use the *Custom HTTP Notification* type. The custom type sends a different payload format that CoPilot cannot parse.

3. Configure the notification:

| Setting | Value |
|---|---|
| **Title** | Give it a descriptive name (e.g., `CoPilot Threshold Webhook`) |
| **URL** | `https://<your-copilot-url>/api/incidents/alerts/create/threshold` |

4. **Save** the notification.

### 4. Attach the Notification to the Event Definition

1. Go back to your Event Definition → **Notifications** tab.
2. Click **Add Notification** and select the HTTP Notification you just created.
3. **Save** the Event Definition.

### 5. Verify the Graylog API header

CoPilot validates inbound Graylog webhook requests using a shared header. Make sure your CoPilot deployment has the `GRAYLOG_API_HEADER_VALUE` environment variable set, and that the Graylog HTTP Notification sends the matching header.

Check with your CoPilot administrator that the Graylog header verification is correctly configured. This is typically set during the initial CoPilot ↔ Graylog integration setup.

---

## How it works end-to-end

```
┌─────────────┐     threshold met      ┌─────────────────────┐
│   Graylog   │ ─────────────────────▶  │  HTTP Notification  │
│  Event Def  │   (count ≥ N in T)      │  (standard type)    │
└─────────────┘                         └─────────┬───────────┘
                                                  │
                                        POST /api/incidents/alerts/create/threshold
                                                  │
                                                  ▼
                                        ┌─────────────────────┐
                                        │      CoPilot        │
                                        │  Incident Mgmt      │
                                        │  (new alert created) │
                                        └─────────────────────┘
```

1. Graylog evaluates the aggregation query on schedule (e.g., every minute).
2. When the threshold condition is met, Graylog fires the Event Definition.
3. The HTTP Notification sends a POST request to CoPilot's `/create/threshold` endpoint with the event payload (including your custom fields).
4. CoPilot validates the Graylog header, extracts the required fields (`CUSTOMER_CODE`, `SOURCE`, `ALERT_DESCRIPTION`, `ASSET_NAME`), and creates a new alert in Incident Management.
5. The alert appears in the CoPilot **Incident Management → Alerts** view and can be triaged, assigned to a case, or trigger downstream automation (e.g., via Shuffle).

---

## Differences from standard alerts

| | Standard alerts | Threshold alerts |
|---|---|---|
| **Trigger** | Single event match | Aggregation count over time window |
| **CoPilot ingestion** | Auto-collected from `gl-events-*` indices | Sent via webhook to `/create/threshold` |
| **Graylog notification type** | Not required (CoPilot polls) | **HTTP Notification** (standard) required |
| **Custom fields** | `COPILOT_ALERT_ID: NONE` added by default | `CUSTOMER_CODE`, `SOURCE`, `ALERT_DESCRIPTION`, `ASSET_NAME` |
| **Underlying event** | Links back to a specific indexed event | No single event — aggregated context only |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Alert not appearing in CoPilot | Notification not attached to Event Definition | Attach the HTTP Notification in the Event Definition's Notifications tab |
| `403 Forbidden` from CoPilot | Graylog header mismatch | Verify `GRAYLOG_API_HEADER_VALUE` matches between CoPilot and Graylog |
| `422 Unprocessable Entity` | Missing required custom fields | Ensure all four fields (`CUSTOMER_CODE`, `SOURCE`, `ALERT_DESCRIPTION`, `ASSET_NAME`) are defined |
| Alert created but missing context | Template variable not resolving | Check that your field templates reference valid event fields (use Graylog's Preview) |
| Used *Custom HTTP Notification* type | Wrong notification type | Delete and recreate using the standard **HTTP Notification** type |

---

## Related pages

- [Alerting → Shuffle (notifications & automation)](./alerting-shuffle.md)
- [Alerts — SIEM view](./alerts-siem.md)
- [Graylog Management (detections)](./graylog-management.md)
- [Incident Management](./incident-management.md)
- [Incident Alerts](./incident-alerts.md)
- [Incident Sources (mapping context)](./incident-sources.md)
