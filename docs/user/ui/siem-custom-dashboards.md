---
title: Custom Dashboards
description: Build native SIEM dashboards for any indexed source — including custom integrations — directly from the CoPilot UI.
---

# Custom Dashboards

**Menu:** SIEM → Dashboards → **Custom dashboards**

**Best for:** Admin / Engineer

CoPilot ships built-in dashboard templates for the integrations it knows about (Wazuh EDR, Office 365, …). **Custom dashboards** cover everything else: any data you already ingest into Graylog / the Wazuh Indexer — a third-party integration, a custom pipeline, a one-off index — can get a native dashboard without code changes or a new built-in template.

A custom dashboard is a *template*: you build it once, then enable it for a customer against one of that customer's [Event Sources](/user/ui/siem-event-sources). The Event Source supplies the index pattern and the time field, so the same dashboard can be reused across customers whose data lives in differently-named indices.

Once enabled, a custom dashboard behaves exactly like a built-in one — it shows up in the enabled dashboards list, opens in the same viewer, supports the same time-range presets, and is visible in the **Customer Portal**.

---

## Prerequisites

- The data must already be indexed and searchable (verify it in [Event Search](/user/ui/siem-event-search)).
- The customer needs at least one **enabled Event Source** pointing at the index pattern that holds the data.

---

## Step 1 — Open the builder

1. Go to **SIEM → Dashboards**
2. Select the customer
3. Click **Custom dashboards**
4. Pick the **Event source** the dashboards will be enabled against
5. Click **New dashboard**

---

## Step 2 — Describe the dashboard

| Field | Description |
|---|---|
| **Title** | Shown in the dashboard list and in the viewer header |
| **Description** | Short summary of what the dashboard shows |
| **Event type / Vendor / Product** | Metadata used to categorise the dashboard card |
| **Icon / Accent color / Tags** | Presentation only |
| **Dashboard filter (Lucene)** | Applied on top of *every* widget filter — the natural place for the query that isolates this integration (e.g. `data_vendor:acronis`) |
| **Availability** | Keep the dashboard scoped to the selected customer, or share it with **all** customers |

A **shared** dashboard is defined once and enabled per customer, each against that customer's own Event Source. This is the recommended setting for a reusable integration dashboard.

---

## Step 3 — Add widgets

Click **Add widget** and choose a type:

| Type | Shows | Needs |
|---|---|---|
| **Stat** | A single count of matching events | — |
| **Histogram** | Events over time | — |
| **Pie** | Distribution across the values of one field | Aggregation field |
| **Bar** | Top values of one field | Aggregation field |
| **Table** | The most recent matching events | Fields to display |

Each widget also takes:

- a **Filter (Lucene)** — ANDed with the dashboard-wide filter
- a **Width** (out of a 12-column grid) and a **Height**
- a **Top values** / **Rows** count for aggregations and tables

Field names are suggested from the live index mapping of the selected Event Source, but the inputs accept free text so you can type a field that is not mapped yet.

!!! tip "Aggregating on text fields"
    If a field is mapped as `text`, CoPilot automatically retries the aggregation against its `.keyword` sub-field — no need to type the suffix yourself.

---

## Step 4 — Preview, then save

Choose an Event Source under **Preview against** and click **Preview** to run the widgets against real data before saving anything. When the result looks right, click **Create dashboard**.

---

## Step 5 — Enable it for a customer

Back in the **Custom dashboards** drawer, with an Event source selected, click **Enable** on the dashboard card. It now appears in the customer's **Enabled Dashboards** list (category `Custom`) and can be opened from there — or from the Customer Portal, if the customer has portal access.

Enabling the same dashboard against a second Event Source gives you two independent dashboards, one per source.

---

## Sharing dashboards between deployments

Every custom dashboard can be exported and imported as a JSON file:

- **Export JSON** (in the editor) downloads the definition.
- **Load JSON** (in the editor) fills the form from a definition — pasted or uploaded — so you can review it before saving.

The exported file keeps its `template_key`, so re-importing it into another CoPilot deployment preserves the dashboard's identity.

---

## Editing and deleting

- **Edit** changes the template in place. Every dashboard already enabled from it picks up the change on the next load — the identifier never changes when you rename a dashboard.
- **Delete** removes the template **and** every dashboard enabled from it, for every customer. The confirmation dialog states this explicitly.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| A widget shows an error instead of data | The Lucene filter or field name doesn't match the index. Verify the query in [Event Search](/user/ui/siem-event-search). |
| A table panel is empty but stats have data | The listed fields don't exist on the matching documents; check the field names in the Event Search field list. |
| **Enable** is disabled | No Event Source is selected, or the customer has no enabled Event Source. |
| The dashboard can't be enabled for another customer | It is scoped to a single customer — edit it and switch **Availability** to all customers. |
