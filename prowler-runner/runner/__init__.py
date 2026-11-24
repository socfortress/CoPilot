"""CoPilot's Prowler runner: runs Prowler scans for copilot-backend (#1328).

The backend owns everything product-facing (cloud accounts, credentials at rest,
schedules, findings, tenancy). This service only runs scans: one ``prowler``
process per scan, with the scan's credentials in that process's environment, and
hands back compact, normalized results.
"""

__version__ = "0.1.0"

PROVIDERS = ("aws", "azure", "gcp", "m365")
