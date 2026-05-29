# SOCFortress MDR

Forward this customer's alerts to the SOCFortress MDR server.

When deployed, every alert created in CoPilot for this customer is sent to the
MDR server (`POST /api/v1/alerts/copilot`). The MDR server then tasks the
customer's collector to fetch the authoritative document from the Wazuh Indexer
and runs its analysis. Alert status changes made in MDR are pushed back to
CoPilot automatically.

## Requirements

- The MDR server must be reachable from CoPilot. Set `MDR_ENABLED=true` and
  `MDR_SERVER_URL` (e.g. `https://mdr-server.socfortress.co:8443`) in CoPilot's
  `.env`.
- The customer must have a registered collector on the MDR side.

## Auth keys

| Key | Description |
| --- | --- |
| `COLLECTOR_UUID` | The MDR collector UUID assigned to this customer. Used to authenticate the alert hand-off to the MDR server. |

## Deploy

After adding the integration with the customer's `COLLECTOR_UUID`, click
**Deploy**. Provisioning validates the collector UUID and marks the integration
active — no Graylog/Grafana resources are created (the MDR server pulls alerts
on demand via the collector).
