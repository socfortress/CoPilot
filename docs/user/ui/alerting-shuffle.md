---
title: Alerting → Shuffle (notifications & automation)
description: How CoPilot triggers Shuffle workflows for alert/case notifications and automation.
---

# Alerting → Shuffle (notifications & automation)

CoPilot integrates with **Shuffle** to run automation/playbooks and send notifications (Teams/Slack/Jira/email/webhooks) when:

- a new **Alert** is ingested into **Incident Management**, or
- an analyst manually triggers a **Case** workflow.

This is the recommended way to extend CoPilot alerting into external systems without needing a custom integration inside CoPilot for every downstream tool.

> **There is now a second, newer notification system.** [Notification routes](./notifications.md) let you send to **email, Microsoft Teams, Shuffle or any webhook**, with per-route triggers and severity filtering — including notifying an analyst when work is assigned to them.
>
> The workflow described on this page still works and is unchanged. But it fires on the **same event** as an *alert is created* route, so a customer configured with both receives **two notifications per alert**. The route form warns you when that applies.

## Video walkthrough

<iframe width="560" height="315" src="https://www.youtube.com/embed/Ko5jLfkSCrk?si=YHEv-wHYhY3FuRUe" title="Revolutionize Your SIEM Alerts: Integrate CoPilot &amp; Shuffle" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>

> 🎥 [Revolutionize Your SIEM Alerts: Integrate CoPilot & Shuffle](https://youtu.be/Ko5jLfkSCrk?si=YHEv-wHYhY3FuRUe)

> ⚠️ **Note:** the video sets the Shuffle connector URL to `https://shuffler.io`. Shuffle Cloud now runs **region-specific** API backends, and your workflow only exists on the backend for your org's region. If your Shuffle org is not in the US region, set the connector URL to your regional endpoint (e.g. `https://eu.shuffler.io`) — otherwise the connector verifies but workflow lookups fail and notifications silently don't run. See the region table in the [full guide](../shuffle-integration.md#step-2-add-the-shuffle-connector-url-api-key-to-copilot).

## Read the full guide

- **CoPilot ↔ Shuffle Integration (Admin/Operator)**: ../shuffle-integration.md

## Related alerting pages

- Notification routes (email / Teams / Shuffle / webhook): ./notifications.md

- Graylog management (detections): ./graylog-management.md
- Incident sources (mapping context): ./incident-sources.md
- Alerts (SIEM view): ./alerts-siem.md
