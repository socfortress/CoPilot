"""Weekly Sysmon noise statistics, sent to SOCFortress (sysmon-sync's report contract v1).

Each CoPilot finds its customers' noisiest Sysmon patterns of the previous ISO week in its own Wazuh indexer, redacts
them, and sends one report per customer per week to SOCFortress's sysmon-sync service (``POST /v1/sysmon/report`` with
the license key, the same service and base URL the default Sysmon config is pulled from). Across the fleet these become
candidates for reviewed exclusions in the installer repository.

Privacy model, in short:

- Sharing is on by default with a per-customer opt-out (which also asks SOCFortress to delete what it already has), and
  ``SYSMON_STATS_SHARING=off`` stops every query and request.
- Only quiet events (Wazuh rule level 5 or lower: no detections), only patterns seen on at least 3 of the customer's
  endpoints, at most 70 per report. No command line is ever queried or sent, nor a destination IP.
- Every value is redacted with an allow-list (redaction.py, dns_policy.py) and checked with sysmon-sync's own rules
  (contract_v1.py, vendored); a value that cannot be made safe drops its pattern. Customers are pseudonyms (an HMAC
  under a secret only this CoPilot has).
- Nothing about a report's values is logged, stored in MinIO or audited: only counts, hashes and reason codes.

Status semantics: per customer and week, a ``terminal`` outcome (sent, refused, no Sysmon events, ...) is never retried;
a ``pending`` one (network error, rate limit, indexer timeout, ...) is retried by a later tick until the week rolls over.
A week that was never sent is not backfilled.

Modules: settings (environment and constants), contract_v1 / contract_v1_rules (the vendored validator), identity
(secret, pseudonyms, jitter), fields (field discovery, the per-event plan), queries (aggregation bodies and parsers),
collector (indexer I/O), redaction and dns_policy (the redactor), report (the report and its local check), config_state
(the report's ``config``), client (HTTP), state (MinIO records), runner (tick, Send now, preview), sharing (opt-out,
withdraw, decommission hooks), status (the page's view).
"""
