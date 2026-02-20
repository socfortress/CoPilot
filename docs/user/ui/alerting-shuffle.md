---
title: Alerting → Shuffle (notifications & automation)
description: How CoPilot triggers Shuffle workflows for alert/case notifications and automation.
---

# Alerting → Shuffle (notifications & automation)

CoPilot integrates with **Shuffle** to run automation/playbooks and send notifications (Teams/Slack/Jira/email/webhooks) when:

- a new **Alert** is ingested into **Incident Management**, or
- an analyst manually triggers a **Case** workflow.

This is the recommended way to extend CoPilot alerting into external systems without needing a custom integration inside CoPilot for every downstream tool.

## Read the full guide

- **CoPilot ↔ Shuffle Integration (Admin/Operator)**: ../../shuffle-integration.md

## Related alerting pages

- Graylog management (detections): ./graylog-management.md
- Incident sources (mapping context): ./incident-sources.md
- Alerts (SIEM view): ./alerts-siem.md
