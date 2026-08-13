# Notifications (Admin/Operator)

CoPilot can send a message when something happens — a new alert lands, an AI investigation finishes, an analyst is assigned a case. You choose **what** triggers it, **who** receives it, **which channel** carries it, and **how the message is worded**.

This guide covers the notification routing engine as a whole, plus setup for each channel: **Email (Resend)**, **Microsoft Teams**, **Shuffle**, and **direct webhooks**.

> **Not to be confused with Notification Workflows.** CoPilot has an older, separate per-customer feature that fires a single Shuffle *workflow* on alert creation, configured under *Customers → (customer) → Notification Workflows*. Both still work. See [Overlap with Notification Workflows](#overlap-with-notification-workflows) before enabling both.

---

## The idea

A **route** is one rule. It answers four questions:

| Question | Field |
|---|---|
| When should this fire? | **Trigger** |
| How severe must it be? | **Minimum severity** |
| Where does it go? | **Channel** + its configuration |
| What does it say? | **Message template** (optional — there's a sensible default) |

You can have as many routes as you like. Every route matching an event fires independently, so one alert can notify a customer's Teams channel *and* a webhook into your automation platform *and* nothing else, depending on what you've configured.

### Two kinds of route

This distinction matters more than any other setting.

**Customer routes** deliver to the end customer. They live under *Customers → (customer) → Notifications* and carry that customer's code. Use them for things the customer should know about: an alert was raised, an investigation concluded.

**Internal routes** deliver to your SOC. They live under *Notifications → Internal Routes* in the main navigation, belong to no customer, and are **admin-only**. Use them for things your team should know about: who picked up which alert.

Assignment notifications are internal by design. If you assign an ACME alert to an analyst, that notification reaches your team — never ACME's channel. This isn't configurable, and it isn't meant to be: telling a customer which of your analysts is handling their incident is rarely intended.

---

## Which trigger do I want?

**This is the single most common source of confusion, so it's worth a section of its own.**

When an alert arrives and AI analysis is enabled for that customer, **two separate events happen minutes apart**:

```
21:35:03   Alert #14 created                    →  fires "An alert is created" routes
21:35:03   Talon investigation starts
21:37:15   Investigation finishes, report saved →  fires "An AI investigation completes" routes
```

They are **different triggers**. A route configured for *an alert is created* will **never** fire when the investigation finishes, no matter how the rest of it is set up.

That matters because **AI content only rides the second event**. If you want the investigation's findings — the summary, or the full report — you need a route with the *An AI investigation completes* trigger. A customer with only an alert-creation route gets the alert notification and nothing else, forever, and **nothing anywhere reports an error**, because a trigger with no subscriber isn't a failure — it's just an event nobody asked about.

Since v0.1.85 the backend log records it explicitly:

```
Notification emit [investigation_complete] alert#14: no route is configured for this trigger; nothing sent.
```

If you expected an AI notification and didn't get one, that line is the first thing to look for.

| You want… | Trigger to use |
|---|---|
| To know an alert happened, immediately | An alert is created |
| The AI's conclusions about an alert | An AI investigation completes |
| The AI's conclusions, but only once an analyst has checked them | An AI report is reviewed |
| Both (two messages) | Two routes, one of each |

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

### Both

| Trigger | Fires when |
|---|---|
| **An AI report is reviewed** | An analyst submits a review of an AI investigation. Once per alert — a second reviewer or a revision does not re-notify. |

This is the only trigger offered on **both** customer and internal routes, because analyst sign-off is legitimately both audiences' business. It's what lets you hold customer delivery until a human has checked the AI's work — see [Two audiences, two moments](#two-audiences-two-moments).

It counts as AI-written content, so a customer-facing review route is governed by the same *Customers → (customer) → AI Report* opt-in as the rest. An internal route is not: if the switch is off, the customer's route is suppressed and **your internal one still fires**.

Assignment triggers only fire on an **actual change**. Re-saving the same assignee sends nothing. By default, assigning something to *yourself* also sends nothing — there's a per-route **Notify on self-assign** option if your team wants the audit trail anyway.

### Severity filtering

**Minimum severity** is inclusive: a route set to *High* fires on High and Critical, not Medium.

For alert creation, severity comes from the Wazuh rule level:

| Rule level | Severity |
|---|---|
| 12–15 | Critical |
| 8–11 | High |
| 4–7 | Medium |
| 1–3 | Low |

**Alerts from sources with no rule level default to `High`.** Office 365, CrowdStrike, Carbon Black, Huntress and similar integrations carry no Wazuh rule level, and they are deliberately loud by default rather than silently filtered out. Change it deployment-wide with `DEFAULT_ALERT_SEVERITY` in your `.env`:

```bash
DEFAULT_ALERT_SEVERITY=Medium   # Critical | High | Medium | Low | Informational
```

> **The AI's severity is a different number.** An investigation assesses the *finding*, which often disagrees with the alert. Alert #14 in our own testing was `Critical` by rule level while its investigation concluded `Medium`. **An *AI investigation completes* route filters on the AI's assessment**, not the alert's — so a route gated at *High* will drop investigations the AI graded Medium, even for a Critical alert. If that surprises you, set AI routes lower than you'd set alert-creation routes.

Assignment notifications are **Informational** — being assigned something isn't a security severity. Set assignment routes to *Informational and above*, or they'll never fire.

---

## Channels

| Channel | Delivers to | Can email the assignee? | Template formats |
|---|---|---|---|
| **Email (Resend)** | Fixed addresses, or whoever an item is assigned to | **Yes** | text, markdown, **html** |
| **Microsoft Teams** | A Teams channel, via an incoming webhook | No | text, markdown |
| **Shuffle** | A Shuffle app in the customer's org | No | text, markdown |
| **Webhook** | Any HTTPS endpoint | No | text, markdown |

Only email can address a *person*. A webhook targets a fixed URL and Teams targets a fixed channel, so "notify whoever this was assigned to" requires the Resend channel.

Only email renders HTML. Markdown and HTML templates are both converted to a formatted email body, with a plain-text part alongside for clients that refuse HTML. On chat channels markdown is already the native format.

**Shuffle is unavailable on internal routes.** A Shuffle integration belongs to a specific customer, and an internal route has no customer — so the option isn't offered there.

---

## Worked examples

Complete recipes. The confusion usually comes from the *combination* of settings rather than any single field, so each of these shows every choice together.

### Email the customer a full AI report after every investigation

The setup most people are actually after when they ask "why isn't the report being emailed?"

| Field | Value |
|---|---|
| Where | *Customers → (customer) → Notifications* |
| Trigger | **An AI investigation completes** |
| Minimum severity | *Informational and above* (the AI's assessment is often Medium — see above) |
| Channel | Email (Resend) |
| Deliver to | A fixed list of addresses |
| To | The customer's security contact |
| Message template | **AI investigation — full report (HTML email)** |

**Also required:** *Customers → (customer) → AI Report* must be **enabled**. It's opt-in, and while it's off every AI notification to that customer is suppressed and logged as `skipped`.

The customer receives the complete write-up — timeline, IOC verdicts, recommended actions — with its tables rendered, in their brand colours.

To send just a short summary instead, use the **AI investigation — customer summary** template. Same route, different template.

### Teams card for Critical alerts only

| Field | Value |
|---|---|
| Where | *Customers → (customer) → Notifications* |
| Trigger | **An alert is created** |
| Minimum severity | *Critical* |
| Channel | Microsoft Teams |
| Webhook URL | From the Teams Workflows app |
| Message template | *(none — the default card is designed for this)* |

Leave the template empty. Teams renders its own card with a severity-coloured header, a facts table and an **Open in CoPilot** link; a custom template replaces the body but not the card structure.

### Email an analyst when they're handed an alert

| Field | Value |
|---|---|
| Where | *Notifications → Internal Routes* (admin only) |
| Trigger | **An alert is assigned** |
| Minimum severity | *Informational and above* ← **required** |
| Channel | Email (Resend) |
| Deliver to | **Whoever it's assigned to** |
| Message template | **Assignment — who and what** |

Two things bite here. Assignment events are always **Informational**, so any higher floor means the route never fires. And this must be an **internal** route — assignment triggers aren't offered on customer routes because they could never match.

Analysts need an email address on their CoPilot account. A missing one is recorded as `failed` with the reason rather than silently falling back to anyone else.

### Push everything into your own automation

| Field | Value |
|---|---|
| Where | *Customers → (customer) → Notifications* |
| Trigger | **An AI investigation completes** |
| Minimum severity | *Informational and above* |
| Channel | Webhook |
| Webhook URL | Your HTTPS endpoint |
| Custom headers | `Authorization: Bearer …` |
| Include full AI report | **On** |
| Message template | *(none — you want the structured JSON, not prose)* |

Leave the template empty so CoPilot sends its structured JSON object. A template replaces the entire body with its rendered output, which is what you want for a provider-specific shape like Discord's `{"content": …}` — and not what you want when you're parsing the payload.

### Two audiences, two moments

Internal first, customer only after a human has checked it. This is the configuration the *An AI report is reviewed* trigger exists for:

- **Route A** — **internal**, *An AI investigation completes*, Teams. Your team sees every investigation the moment it lands, unreviewed.
- **Route B** — **customer**, *An AI report is reviewed*, email, full-report template. The customer hears nothing until an analyst has signed off in *AI Analyst → (report) → Review*.

Nothing reaches the customer automatically; the analyst's review is the release gate.

*An AI report is reviewed* is the **only trigger available on both scopes**, so you can also run a third route — internal, same trigger — if your team wants a record of who signed off on what.

A review fires the notification **once per alert**. A second reviewer, or someone revising their own review, does not re-notify.

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

Under *Customers → (customer) → Notifications* (or *Notifications → Internal Routes* for assignments):

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

**Include full AI report** is a checkbox on the route, not something you reference in a template. When it's on, the report's extra fields are merged into that same JSON object.

If you set a **message template**, its rendered output is sent as the raw body *instead* of the structured object — which is how you match a provider-specific shape like Discord's `{"content": …}` or Slack's `{"text": …}`. If you're parsing the payload programmatically, leave the template empty.

---

## Message templates

Every route sends a sensible default message. Templates let you change the wording, the structure, and — on email — the formatting.

There are **two ways** to set one, and they don't behave the same.

### Named templates (recommended)

*Notifications → Message Templates* in the main navigation. Write a template once, attach it to as many routes as you like, edit it in one place.

A named template carries:

| Property | Meaning |
|---|---|
| **Name** | How you'll recognise it in the route form |
| **Format** | `text`, `markdown` or `html` — decides how channels render it |
| **Subject** | Optional. Email only; other channels ignore it. |
| **Body** | The message itself |
| **Trigger** | Optional. Restricts the template to one trigger so it can't be attached where its variables don't exist. |
| **Customer** | Optional. Leave empty to share it with every customer. |

### Inline templates (per-route override)

The **Custom message body** field on an individual route. Use it when one route needs to deviate without forking a shared template.

### Precedence

**Inline → named → channel default.** An inline body always wins; if there's none, the route's named template is used; if there's neither, you get the channel's built-in wording.

### Writing a template

Templates are [Jinja](https://jinja.palletsprojects.com/en/stable/templates/) — conditionals, loops and filters all work:

```jinja
*{{ severity }}* — {{ alert_name }}
Customer: `{{ customer_code }}`
{% if context.asset_name %}Asset: {{ context.asset_name }}{% endif %}
{% if link_url %}Open in CoPilot: {{ link_url }}{% endif %}
```

Available variables:

| Variable | Contains |
|---|---|
| `{{ severity }}` | Critical / High / Medium / Low / Informational |
| `{{ customer_code }}` | Customer code. Empty on internal routes. |
| `{{ summary }}` | The event's body text |
| `{{ subject }}` | One-line title |
| `{{ link_url }}` | Deep link into CoPilot. May be empty. |
| `{{ entity_type }}` / `{{ entity_id }}` | `alert`, `case` or `case_task`, and its id |
| `{{ trigger }}` | Which trigger fired this |
| `{{ assignee }}` / `{{ actor }}` | Assignment triggers only |
| `{{ context.… }}` | Per-event extras — `context.asset_name`, `context.rule_level`, `context.iocs` |
| `{{ context.reviewer }}` / `{{ context.verdict }}` | Review trigger only — who signed off, and their verdict |
| `{{ branding.… }}` | Customer logo and brand colours — `logo`, `title`, `accent`, `accent_strong`, `accent_text` |
| `{{ context.ai_report.… }}` | The AI investigation report — see below |

`{{ alert_id }}`, `{{ alert_name }}` and `{{ report_url }}` are kept as aliases so anything written before templates became Jinja still works.

> **A misspelled variable is an error, not an empty string.** `{{ summry }}` doesn't render blank — the whole template fails and the route falls back to the channel default, with the reason recorded on the dispatch-log row. The editor validates when you save, and the live preview shows exactly what will be sent.
>
> The one exception is `context.…`, where a missing key *does* render empty. The same trigger legitimately carries different keys on different events — one alert has an asset name, the next doesn't — so guard with `{% if context.asset_name %}` rather than assuming it's there.

### Including the AI investigation report

`{{ context.ai_report }}` gives a template the full investigation:

| Field | Contains |
|---|---|
| `.html` | The report rendered as HTML, tables and all. **Use this in an `html` template.** |
| `.markdown` | The raw markdown source |
| `.summary` | The short summary |
| `.recommended_actions` | The AI's suggested next steps |
| `.severity` | The AI's assessment — **not** the alert's severity |
| `.iocs` | Indicators, each with `.value`, `.type`, `.vt_verdict`, `.vt_score` |
| `.ioc_count` | How many there were in total |

Always guard it — most alerts have no investigation:

```jinja
{% if context.ai_report %}
  {{ context.ai_report.html }}
{% else %}
  {{ summary }}
{% endif %}
```

The report is only fetched when a template mentions `ai_report`, so templates that don't reference it cost nothing.

### Built-in templates

Seven ship with every deployment, as working starting points and as worked examples of the syntax:

| Template | For |
|---|---|
| **Alert — concise** | One-liner for high-volume chat channels |
| **Alert — detailed with IOCs** | Full context including indicators |
| **Assignment — who and what** | Internal routes |
| **AI investigation — customer summary** | Plain-language wrap-up for the end customer |
| **AI report reviewed — sign-off** | Who reviewed an investigation and what they concluded |
| **AI investigation — full report (HTML email)** | The complete write-up with rendered tables, in the customer's brand colours |
| **Branded email — HTML** | A branded shell for any trigger |

Built-ins are **read-only** — the next startup would recreate them anyway. Use **Duplicate** to get an editable copy.

---

## Sending something manually

Sometimes you want to push one specific alert or case to a channel — outside the triggers and severity filters entirely.

Open an alert or case and choose **Send to channel…**.

| | |
|---|---|
| **Where it can go** | Only a **configured route** — the item's own customer's routes, plus internal ones. There's no free-text address field, by design. |
| **Who can do it** | Internal routes: analysts and admins. Customer-facing routes: **admins only**. |
| **Include the AI investigation report** | Attaches the full write-up. Alerts only; refused if the alert has no investigation. |
| **Preview** | Renders exactly what will be sent, without sending it |

This sends a **real** notification: it consumes provider quota and is recorded in the dispatch log with `trigger_source = manual`. Sending twice sends twice — deliberately, since clicking send twice on purpose should work.

The customer AI opt-out still applies. If *Customers → (customer) → AI Report* is off, including the report is refused rather than quietly dropped.

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

A row also carries a **template error** when a custom template failed and the channel default went out in its place — so a broken template is visible without having to reproduce it.

### Nothing arrived

Work down this list:

1. **Is there a route for that trigger at all?** The most common cause by far. An *alert is created* route does not fire when an AI investigation completes — see [Which trigger do I want?](#which-trigger-do-i-want). Check the backend log for `no route is configured for this trigger`.
2. **Is the route enabled?**
3. **Is the severity high enough?** Assignment routes must be set to *Informational and above*. AI routes filter on the **AI's** assessment, which is often lower than the alert's.
4. **Right scope?** Assignment notifications only reach **internal** routes. A customer route with an assignment trigger can never fire — which is why the UI doesn't offer that combination.
5. **Check the dispatch log.** A `failed` row carries the provider's own message. A `skipped` row says which rule applied. **No row at all** means no route matched — go back to step 1.
6. **Is the connector verified?** Connectors → Resend → Verify.

### AI report notifications aren't arriving for one customer

There's a separate switch: *Customers → (customer) → AI Report*. It controls whether AI-written findings may reach that customer at all, and it's **opt-in** — a customer who has never been enabled is disabled.

When it's off, AI notifications to that customer's routes are suppressed and logged as `skipped`. Internal routes are unaffected, so you can keep running investigations while keeping results in-house.

### The email arrived but the formatting is wrong

- **Asterisks showing as literal `*text*`** — the template's format is `text`. Change it to `markdown` and email will render it. Chat channels treat markdown natively either way.
- **Tables showing as rows of `|` characters** — same cause. Markdown or HTML format renders them properly on email; chat channels can't render tables at all.
- **HTML tags visible in the message** — an `html` template sent to a chat channel. Only email renders HTML.

### The template previewed fine but the real message is the default

Almost always a `context.…` variable that exists on the sample event and not on the real one. The preview uses a fully-populated sample; real events are sparser. Guard every `context.…` reference with `{% if %}`.

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
| An AI report is reviewed | **Customer and internal** |
| An alert / case / case task is assigned | Internal |

### Channel capabilities

| Channel | Assignee delivery | Internal routes | HTML | Secret |
|---|---|---|---|---|
| Email (Resend) | Yes | Yes | Yes | API key on the connector |
| Microsoft Teams | No | Yes | No | The webhook URL itself |
| Webhook | No | Yes | No | Custom headers |
| Shuffle | No | **No** | No | Deployment API key |

### Environment variables

```bash
# Email (Resend)
RESEND_URL=https://api.resend.com
RESEND_API_KEY=re_your_key_here
RESEND_FROM_ADDRESS=alerts@yourdomain.com

# Severity assumed for alerts whose source carries no rule level.
# Default: High
DEFAULT_ALERT_SEVERITY=High

# Base URL used to build "Open in CoPilot" links. Without it, links are omitted.
COPILOT_URL=https://copilot.yourdomain.com
```

Teams and webhook routes need no environment configuration — their URLs live on the route. Shuffle uses the existing deployment-wide `SHUFFLER_API_KEY`.

---

## Related

- [CoPilot ↔ Shuffle Integration](./shuffle-integration.md)
- [Alerting → Shuffle (notifications)](./ui/alerting-shuffle.md)
- [Connectors](./ui/connectors.md)
- [Customers](./ui/customers.md)
