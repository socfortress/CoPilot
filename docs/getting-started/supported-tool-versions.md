# Supported tool versions

CoPilot integrates with multiple upstream tools (SIEM, EDR, SOAR, DFIR, dashboards). In practice, “supported” means:

- CoPilot’s connectors/provisioning logic has been **tested** against these versions
- API endpoints and payloads CoPilot relies on are stable in these versions

If you’re running something older/newer, it *may* work — but this table is the **known-good** baseline.

> If you hit a version-specific issue, open a GitHub issue with:
> CoPilot version, tool version, and the exact failing endpoint/UI path.

---

## Version compatibility matrix

| Tool | Known-good / tested versions | Notes |
|---|---:|---|
| **Graylog** | **6.x** | CoPilot relies on Graylog Event Definitions writing to `gl-events_*` and uses fields that differ in older Graylog versions (ex: config differences around `event_limit`). |
| **Wazuh (Manager)** | **4.14.2** | CoPilot’s vulnerability flows use Wazuh APIs that changed in newer Wazuh versions; 4.8+ is required for the “new” vulnerability API logic. |
| **Grafana** | **12.3.3** | CoPilot provisions/uses orgs, dashboards, and datasources via Grafana’s HTTP API; Grafana 9+ is the baseline for current provisioning workflows. |
| **Shuffle** | **(current)** | CoPilot invokes Shuffle workflows via API key + workflow ID. Recommended: run the latest stable Shuffle (cloud UI + on-prem worker/location). |
| **Velociraptor** | **0.75.6 (current)** | CoPilot integrates with Velociraptor via its API for hunting/collection workflows. Recommended: stay on the latest stable 0.7.x branch. |

---

## Where to check versions

- **CoPilot version:** bottom-left of the CoPilot UI (or the Git tag/release you deployed)
- **Graylog version:** Graylog **System → Overview**
- **Wazuh version:** Wazuh dashboard footer / Wazuh API `/version`
- **Grafana version:** bottom-left footer
- **Shuffle version:** Shuffle admin/about (or image tag if self-hosted)
- **Velociraptor version:** server UI footer / `velociraptor --version`
