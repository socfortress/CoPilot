---
title: Notifications (routes & channels)
description: Send alerts, AI investigation results and assignment events to email, Teams, Shuffle or a webhook.
---

# Notifications (routes & channels)

CoPilot sends a message when something happens — a new alert lands, an AI investigation finishes, an analyst is assigned a case. You choose the **trigger**, the **severity floor**, and the **channel**.

Four channels ship today:

| Channel | Delivers to |
|---|---|
| **Email (Resend)** | Fixed addresses, or whoever an item is assigned to |
| **Microsoft Teams** | A Teams channel, via a Workflows webhook |
| **Shuffle** | An app in the customer's Shuffle org |
| **Webhook** | Any HTTPS endpoint |

## Where to configure it

**Per-customer routes** — *Customers → (customer) → Notifications*

Things the customer should know about: an alert was raised, an investigation concluded.

**Internal routes** — *Internal Notifications* in the main navigation (admin only)

Things your SOC should know about: who picked up which alert. These belong to no customer, which is the point — assigning an ACME alert to an analyst notifies your team, never ACME.

## The one thing to know

**Assignment notifications are internal by design.** They only reach internal routes. A customer route with an assignment trigger could never fire, so the interface doesn't offer that combination.

If you want the assignee emailed directly, use the **Email (Resend)** channel with *Deliver to → Whoever it's assigned to*. It's the only channel that can address a person; a webhook targets a URL and Teams targets a channel.

## Testing

Every saved route has a **Send test** button. It sends a real notification through the real path, so it consumes quota and appears in the dispatch log like any other.

For Teams, look at the channel afterwards rather than trusting the result. A malformed payload returns `200 OK` and displays nothing.

## Read the full guide

- **Notifications (Admin/Operator)**: ../notifications.md — setup for each channel, quota management, message templates, and troubleshooting

## Related pages

- Alerting → Shuffle (legacy notification workflows): ./alerting-shuffle.md
- Connectors (verify the Resend connector): ./connectors.md
- Customers: ./customers.md
