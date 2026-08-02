# Notifications (Admin/Operator)

CoPilot can send a message when something happens — a new alert lands, an AI investigation finishes, an analyst is assigned a case. You choose **what** triggers it, **who** receives it, and **which channel** carries it.

This guide covers the notification routing engine as a whole, plus setup for each channel: **Email (Resend)**, **Microsoft Teams**, **Shuffle**, and **direct webhooks**.

> **Not to be confused with Notification Workflows.** CoPilot has an older, separate per-customer feature that fires a single Shuffle *workflow* on alert creation, configured under *Customers → (customer) → Notification Workflows*. Both still work. See [Overlap with Notification Workflows](#overlap-with-notification-workflows) before enabling both.

---

## The idea

A **route** is one rule. It answers three questions:

| Question | Field |
|---|---|
| When should this fire? | **Trigger** |
| How severe must it be? | **Minimum severity** |
| Where does it go? | **Channel** + its configuration |

You can have as many routes as you like. Every route matching an event fires independently, so one alert can notify a customer's Teams channel *and* a webhook into your automation platform *and* nothing else, depending on what you've configured.

### Two kinds of route

This distinction matters more than any other setting.

**Customer routes** deliver to the end customer. They live under *Customers → (customer) → Notifications* and carry that customer's code. Use them for things the customer should know about: an alert was raised, an investigation concluded.

**Internal routes** deliver to your SOC. They live under *Internal Notifications* in the main navigation, belong to no customer, and are **admin-only**. Use them for things your team should know about: who picked up which alert.

Assignment notifications are internal by design. If you assign an ACME alert to an analyst, that notification reaches your team — never ACME's channel. This isn't configurable, and it isn't meant to be: telling a customer which of your analysts is handling their incident is rarely intended.

---

## Triggers

### Customer-facing

| Trigger | Fires when |
|---|---|
| **An alert is created** | A new alert is ingested. Recurrences of an existing open alert do **not** re-fire. |
| **An AI investigation completes** | Talon finishes investigating an alert and writes its report back. |

### Internal

| Trigger | Fires when |
|---|---|
| **An alert is assigned** | An alert's assignee changes |
| **A case is assigned** | A case's assignee changes |
| **A case task is assigned** | A task within a case is assigned |

Assignment triggers only fire on an **actual change**. Re-saving the same assignee sends nothing. By default, assigning something to *yourself* also sends nothing — there's a per-route **Notify on self-assign** option if your team wants the audit trail anyway.

### Severity filtering

**Minimum severity** is inclusive: a route set to *High* fires on High and Critical, not Medium.

For alert creation, severity comes from the Wazuh rule level (12–15 Critical, 8–11 High, 4–7 Medium, 1–3 Low). Alerts from sources with no rule level are treated as **Medium** so they aren't silently filtered out.

Assignment notifications are **Informational** — being assigned something isn't a security severity. Set assignment routes to *Informational and above*, or they'll never fire.

---

## Channels

| Channel | Delivers to | Can email the assignee? |
|---|---|---|
| **Email (Resend)** | Fixed addresses, or whoever an item is assigned to | **Yes** |
| **Microsoft Teams** | A Teams channel, via an incoming webhook | No |
| **Shuffle** | A Shuffle app in the customer's org | No |
| **Webhook** | Any HTTPS endpoint | No |

Only email can address a *person*. A webhook targets a fixed URL and Teams targets a fixed channel, so "notify whoever this was assigned to" requires the Resend channel.

**Shuffle is unavailable on internal routes.** A Shuffle integration belongs to a specific customer, and an internal route has no customer — so the option isn't offered there.

---

## Setting up Email (Resend)

Resend is a transactional email service. Its free tier covers 1,000 emails per month.

### 1. Create a Resend account and API key

1. Sign up at [resend.com](https://resend.com)
2. Create an API key. A **send-only** ("Sending access") key is sufficient and recommended — CoPilot never needs to manage your account.
3. **Verify a sending domain** under *Domains*. Until you do, Resend only delivers to the email address that owns the account, which is fine for testing and useless in production.

### 2. Configure the connector

Add these to your `.env` and restart CoPilot:

```bash
RESEND_URL=https://api.resend.com
RESEND_API_KEY=re_your_key_here
# Must be on a domain you verified in Resend.
RESEND_FROM_ADDRESS=alerts@yourdomain.com
```

Then go to **Connectors**, find **Resend**, and click **Verify**.

> A send-only key is *expected* to report success here even though CoPilot probes a management endpoint it can't reach. Verification recognises restricted keys and treats them as valid. If you used a full-access key, verification additionally reports which sending domains are verified.

### 3. Create a route

Under *Customers → (customer) → Notifications* (or *Internal Notifications* for assignments):

| Field | Notes |
|---|---|
| **Channel** | Email (Resend) |
| **Deliver to** | *A fixed list of addresses*, or *Whoever it's assigned to* |
| **To** | Recipients. Hidden when delivering to the assignee. |
| **From** | Optional. Overrides `RESEND_FROM_ADDRESS`; must be on a verified domain. |
| **Subject prefix** | Defaults to `[CoPilot]` |
| **Max emails per hour** | Defaults to 20. Clear it to disable throttling. |

Click **Send test** to confirm delivery before relying on it.

### Watch the quota

The 1,000/month free tier is **shared across your entire deployment** — every customer's routes draw from the same allowance. That's roughly 33 emails per day for everyone combined.

The route form shows current usage and warns as the month fills. Two things keep it under control:

- **Minimum severity.** An alert-creation route set to *Informational* on a busy customer will exhaust the tier quickly. Start at *High*.
- **Max emails per hour.** A per-route ceiling, so one noisy route can't drain the allowance for everybody. Throttled sends are recorded in the dispatch log with the reason.

If you need more, Resend's paid plans raise the limit and nothing in CoPilot needs to change.

### Notifying the assignee

Set **Deliver to** → *Whoever it's assigned to*. At delivery time CoPilot looks up the assignee's CoPilot account and uses the email address on it.

This means analysts must have a valid email on their user account. If one is missing, the notification is recorded as failed with the reason — it won't silently vanish, and it won't fall back to the static list.

---

## Setting up Microsoft Teams

### 1. Create a webhook in Teams

Microsoft retired the old Office 365 connectors in 2026. The current mechanism is the **Workflows** app:

1. In Teams, go to the channel you want notifications in
2. **More options (…)** next to the channel → **Workflows**
3. Choose the **Send webhook alerts to a channel** template
4. Configure and save, then **copy the webhook URL**

### 2. Create a route

Choose **Microsoft Teams** as the channel and paste the URL. That's the only field.

Then click **Send test** — and actually look at Teams.

> **Why that matters here specifically.** If the payload shape is wrong, Teams responds `200 OK` and displays nothing. A successful-looking test with no visible card means something is wrong. A correct test produces a card with a coloured header and a working **Open in CoPilot** link.

### What the card looks like

The header is coloured by severity — red for Critical and High, amber for Medium, green for Low — which makes a busy channel scannable. Below it, a facts table (customer, entity, assignee) and the message body.

### Limits worth knowing

- **28 KB per message.** Teams rejects anything larger. A long AI report is truncated with a note saying so, and the deep link is preserved so the full detail is one click away.
- **~4 requests per second.** Above that Teams throttles and CoPilot records the notification as failed with a rate-limit message. This is transient — it means retry later, not that anything is misconfigured.

---

## Setting up Shuffle

Shuffle routes deliver through a customer's own authenticated Shuffle org, giving access to its app catalogue (Slack, Outlook, Jira, and several thousand more).

1. Add a **Shuffle integration** for the customer — *Customers → (customer) → Notifications → Shuffle integrations*
2. Create a route with **Shuffle** as the channel
3. Pick the integration, then the app within it
4. Set a **destination hint** — a channel name, email address or handle. This is prepended to the outgoing message so Shuffle's app agent knows where to deliver.

For the wider Shuffle setup, see [CoPilot ↔ Shuffle Integration](./shuffle-integration.md).

---

## Setting up a webhook

The generic option: an HTTPS POST to any endpoint.

| Field | Notes |
|---|---|
| **Webhook URL** | Required, must be `https://` |
| **Method** | POST or PUT |
| **Custom headers** | Optional. For `Authorization`, `X-API-Key` and similar. |
| **Include full AI report** | Adds the report markdown, recommended actions and IOC list to the payload |

By default CoPilot sends a structured JSON object:

```json
{
  "customer_code": "00001",
  "alert_id": 42,
  "alert_name": "Mimikatz signature detected",
  "severity": "Critical",
  "summary": "Credential dumping observed on WKSTN-04.",
  "report_url": "https://copilot.example.com/alerts/42",
  "text": "…the rendered message body…"
}
```

If you set a **custom message template**, its rendered output is sent as the raw body instead — which is how you match a provider-specific shape like Discord's `{"content": …}` or Slack's `{"text": …}`.

---

## Custom message templates

Any route can override the default wording. Templates use `{{token}}` substitution:

| Token | Contains |
|---|---|
| `{{customer_code}}` | Customer code |
| `{{alert_id}}` / `{{entity_id}}` | The alert, case or task id |
| `{{alert_name}}` | Alert title |
| `{{severity}}` | Critical / High / Medium / Low / Informational |
| `{{summary}}` | The default one-paragraph summary |
| `{{report_url}}` | Deep link back into CoPilot |
| `{{assignee}}` | Who it was assigned to (assignment triggers) |
| `{{actor}}` | Who did the assigning |
| `{{entity_type}}` | `alert`, `case` or `case_task` |

On webhook routes only, `{{report}}` injects the full AI report as a JSON object.

---

## Testing and troubleshooting

### Send test

Every saved route has a **Send test** button. It sends a **real** notification through the real path — so it consumes quota and appears in the dispatch log, exactly like a live one. That's deliberate: a test that took a different path wouldn't prove much.

### The dispatch log

*Customers → (customer) → Notifications → Dispatch log* records every attempt:

| Status | Meaning |
|---|---|
| **sent** | The provider accepted it |
| **failed** | It didn't go out — the reason is recorded |
| **skipped** | Deliberately not sent: rate limit, self-assignment, or the customer's AI reports are disabled |

`skipped` is not an error. It's CoPilot recording a decision it made, which is usually what you want to see when asking "why didn't I get an email".

### Nothing arrived

Work down this list:

1. **Is the route enabled?**
2. **Does the trigger match?** An assignment won't fire an *alert is created* route.
3. **Is the severity high enough?** Assignment routes must be set to *Informational and above*.
4. **Right scope?** Assignment notifications only reach **internal** routes. A customer route with an assignment trigger can never fire — which is why the UI doesn't offer that combination.
5. **Check the dispatch log.** A `failed` row carries the provider's own message. A `skipped` row says which rule applied.
6. **Is the connector verified?** Connectors → Resend → Verify.

### AI report notifications aren't arriving for one customer

There's a separate switch: *Customers → (customer) → AI Report*. It controls whether AI-written findings may reach that customer at all, and it's **opt-in** — a customer who has never been enabled is disabled.

When it's off, AI notifications to that customer's routes are suppressed and logged as `skipped`. Internal routes are unaffected, so you can keep running investigations while keeping results in-house.

---

## Overlap with Notification Workflows

CoPilot has an older per-customer feature — *Customers → (customer) → Notification Workflows* — that fires a single Shuffle workflow when an alert is created.

That still works and is untouched. But it fires on the **same event** as an *alert is created* route, so a customer with both configured gets **two notifications per alert**.

Both are opt-in, so this only happens if you set up both. The route form warns you when it applies. If you see that warning, disable whichever you don't want.

---

## Reference

### Trigger → scope

| Trigger | Routes |
|---|---|
| An alert is created | Customer |
| An AI investigation completes | Customer |
| An alert / case / case task is assigned | Internal |

### Channel capabilities

| Channel | Assignee delivery | Internal routes | Secret |
|---|---|---|---|
| Email (Resend) | Yes | Yes | API key on the connector |
| Microsoft Teams | No | Yes | The webhook URL itself |
| Webhook | No | Yes | Custom headers |
| Shuffle | No | **No** | Deployment API key |

### Environment variables

```bash
# Email (Resend)
RESEND_URL=https://api.resend.com
RESEND_API_KEY=re_your_key_here
RESEND_FROM_ADDRESS=alerts@yourdomain.com
```

Teams and webhook routes need no environment configuration — their URLs live on the route. Shuffle uses the existing deployment-wide `SHUFFLER_API_KEY`.

---

## Related

- [CoPilot ↔ Shuffle Integration](./shuffle-integration.md)
- [Alerting → Shuffle (notifications)](./ui/alerting-shuffle.md)
- [Connectors](./ui/connectors.md)
- [Customers](./ui/customers.md)
