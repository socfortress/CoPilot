---
title: Case templates
description: Reusable investigation playbooks with predefined tasks and timeline auditing for cases.
---

# Case templates

**Menu:** Incident Management → Case Templates

**Best for:** Admin / Analyst (template ownership is restricted to these roles)

Case templates are reusable **investigation playbooks** you attach to cases. Each template defines a set of tasks (with optional guidelines) that get snapshot-copied onto a new case when the template matches. Customers see the resulting tasks read-only on their portal so they know what's being worked on.

Templates address three real problems:

- **Investigation consistency** — every case for a given alert source follows the same checklist
- **Auditability** — task status changes, comments, and case mutations all land in a per-case timeline
- **Onboarding** — new analysts don't have to memorize the playbook; the case carries it

---

## Where templates apply

A template has three optional scoping fields:

| Field | Effect | Example |
|---|---|---|
| `customer_code` | Restricts the template to one customer. Empty = global. | `ACME` |
| `source` | Restricts the template to one alert source. Empty = any source. | `wazuh` |
| `is_default` | This is the fallback template within its (customer_code, source) scope. | true / false |

When a case is created **from an alert**, the backend picks the most specific matching template using this priority:

1. `customer_code` + `source` exact match
2. `customer_code` only (source IS NULL)
3. `source` only (customer_code IS NULL)
4. Global default (`is_default=true` with both NULL)

Each step short-circuits the next on first match. Within a step, ties are broken by `is_default` first, then by most-recently-created.

> **First-alert-wins.** When a case is created from an alert, the template is picked from that alert's `(customer_code, source)`. If you later link more alerts to the case, additional templates are **not** auto-applied — analysts can manually apply more via the case's Tasks tab if needed.

---

## Authoring a template

**Menu:** Incident Management → Case Templates → **New template**

| Field | Required | Notes |
|---|---|---|
| Name | yes | Short, recognizable. Shown in the picker on case creation. |
| Description | no | Free-form context for analysts. |
| Customer code | no | Empty = global. |
| Alert source | no | Empty = any source. |
| Default for scope | no | Marks this as the fallback within its (customer, source) pair. Only one default per scope; activating one auto-demotes any other. |
| Tasks | yes | At least one task. Each task has title, description, guidelines, mandatory toggle, and order. |

### Task fields

| Field | Effect |
|---|---|
| Title | Short statement of what to do (e.g., "Identify affected assets") |
| Description | Longer explanation — what success looks like |
| Guidelines | Step-by-step or links to runbooks. Rendered collapsibly under each task on the case Tasks tab. |
| Mandatory | If true, **NOT_NECESSARY** is rejected and closing the case with this task incomplete fires a soft warning. |
| Order | Drag arrows in the editor reorder tasks; lower order_index renders first. |

> Edits to a template **do not** mutate task snapshots already attached to real cases. Each `CaseTask` row is a copy made at template-application time. This way historical investigations stay locked to the template version that was in effect when they were opened.

---

## Tasks on a real case

**Menu:** any case → **Tasks** tab

Analysts see:

- The full task list (status, evidence notes, completion attribution)
- A status dropdown per task: **TODO**, **DONE**, **NOT_NECESSARY** (last is greyed out for mandatory tasks)
- An evidence textarea where you can paste logs, command output, screenshots-as-text, or links
- "Add task" — for one-off custom tasks added during the investigation
- "Apply template" — to layer another template's tasks onto the case (e.g., add an EDR-specific checklist after a Wazuh template was already applied)

Customers see the same list **read-only** on the customer portal. They cannot change status, edit evidence, or add tasks.

---

## Soft warning on close

When you try to close a case where one or more **mandatory** tasks are not marked DONE, a confirmation modal appears listing the incomplete tasks. You can:

- **Cancel** — closes the modal, leaves the case in its current status
- **Close anyway** — closes the case and records `forced=true` in the timeline so the override is auditable

The intent is to remind, not block. Mandatory + soft warning gives consistency without forcing analysts to lie ("I marked it done so I could close it") — the override is captured honestly in the audit trail.

---

## Timeline tab

**Menu:** any case → **Timeline** tab

Append-only audit log of meaningful case mutations. One row per:

- Case created (manual or from alert)
- Status change (with the `forced=true` flag when the soft warning was bypassed)
- Assignment, escalation
- Alert link / unlink (single or bulk)
- Comment added (with a short snippet preview)
- Template applied
- Task added (template-derived or custom)
- Task status change
- Task evidence comment

Customer portal shows the same timeline read-only.

---

## Examples

### Wazuh global default

```
Name:          Wazuh — Default
Source:        wazuh
Customer:      (empty — global)
Default:       yes
Tasks:
  1. Triage alert                        (mandatory)
  2. Identify affected assets             (mandatory, with guidelines)
  3. Check Wazuh agent for related events (mandatory)
  4. Document findings                    (optional)
  5. Notify customer                      (optional, NOT_NECESSARY allowed)
```

Result: any case created from a Wazuh alert (regardless of customer) gets these five tasks pre-populated. Closing the case requires steps 1–3 to be DONE or the soft warning fires.

### Customer-specific override

```
Name:          ACME — Wazuh
Source:        wazuh
Customer:      ACME
Default:       yes
Tasks:
  1. Triage alert                        (mandatory)
  2. Identify affected assets             (mandatory)
  3. Check ACME-specific runbook in wiki  (mandatory, guidelines link)
  4. Page on-call if business-hours       (mandatory)
```

Because `(customer=ACME, source=wazuh)` is more specific than `(customer=any, source=wazuh)`, ACME's Wazuh cases get this template instead of the global one.

### EDR-specific addon

```
Name:          CrowdStrike — Investigation
Source:        crowdstrike
Customer:      (empty)
Default:       no
Tasks:
  1. Pull process tree from EDR
  2. Identify network connections
  3. Collect memory dump if hash unknown  (guidelines: link to runbook)
```

Marked non-default. Auto-applies on create-from-CrowdStrike-alert. Analysts can also manually apply this template to a Wazuh case mid-investigation if EDR work becomes relevant.

---

## Permissions summary

| Capability | Admin | Analyst | Customer User |
|---|---|---|---|
| Manage templates (create / edit / delete) | ✅ | ✅ | — |
| Apply template to case | ✅ | ✅ | — |
| Add custom case task | ✅ | ✅ | — |
| Update case task status / evidence | ✅ | ✅ | — |
| Delete case task | ✅ | ✅ | — |
| View case tasks | ✅ | ✅ | ✅ (read-only) |
| View case timeline | ✅ | ✅ | ✅ (read-only) |
| Close case with incomplete mandatory tasks | ✅ | ✅ | — |

---

## How to use templates well

The mechanics above describe what templates *can* do. This section is about *how to actually use them* so they accelerate investigations instead of cluttering them.

### Start with one global default per source, then layer

Resist the urge to author per-customer templates on day one. The path that scales:

1. **Pick your top 2–3 alert sources** (Wazuh, CrowdStrike, Velociraptor — whatever drives the most cases). Author one **global default** per source. Each should have 3–6 mandatory tasks that capture the universal triage flow, plus 2–4 optional tasks for common follow-ups.
2. **Run for two weeks.** Watch which tasks consistently get marked NOT_NECESSARY. Watch what custom tasks analysts add (the Tasks tab "Add task" button — those are unmet template needs). Track close-with-force events in the timeline.
3. **Tune the global default** based on what you saw. Demote noisy mandatory tasks to optional, promote frequently-added custom tasks into the template.
4. **Only then** start adding customer-specific overrides for the customers that actually have a different runbook (PCI environments, regulated industries, customer-specific evidence requirements, etc.).

You can always create more templates. Removing them later is harder once analysts have memorized the workflow.

### Mandatory discipline — what *should* block close

The soft warning fires on close when a mandatory task isn't DONE. The override is recorded as `forced=true` in the timeline.

A task should be **mandatory** only if:

- Skipping it would leave you unable to answer "what did you actually find?" later
- Skipping it would fail a compliance/audit review
- Skipping it would leave the customer with an unsupported claim ("the alert was benign")

A task should be **optional** if:

- It only applies in some scenarios (e.g., "Pull memory dump" — only matters if hash is unknown)
- It's nice-to-have but the case can close honestly without it
- It's expensive (analyst time, customer time) and not always justified

> **Anti-pattern:** marking everything mandatory. Analysts will start force-closing routinely, the timeline fills with `forced=true`, and the soft warning becomes background noise instead of a real safety net.

### Use guidelines as the runbook quick-reference

The `guidelines` field renders as a collapsible panel under each task. Treat it as the **5-second runbook** — what the analyst needs without leaving the case page.

Good guidelines content:

- 1–3 sentences of "what success looks like for this task"
- A direct link to the deeper runbook in your wiki/SharePoint/Confluence
- 2–3 bullet hints if there's a common gotcha
- Actual command snippets if the task involves running something

```
Bad:  "Investigate the alert."
Good: "Confirm the alert isn't a known false positive (check our exception list
       at <wiki link>). If new, pull the matching events from the last 24h via
       Graylog query: source.ip:X.X.X.X AND event.action:authentication_failure"
```

### Evidence comments are the compliance trail

Every task has an evidence comment textarea. The customer-portal user sees this read-only.

What to put there:

- **Logs / command output** — paste the actual snippet, don't just describe it
- **Reference IDs** — Jira ticket, ServiceNow change number, Velociraptor hunt ID, Graylog query URL
- **Decisions and reasoning** — "marked NOT_NECESSARY because the affected host is decommissioned, see asset CMDB"
- **Customer communication** — "notified customer at 14:32 EST via portal comment"

What *not* to put there:

- Sensitive data the customer shouldn't see (the customer-portal will surface it)
- Internal-team chatter (use case Comments tab for that — also visible to customer but framed as conversation)

### Reorder for natural investigation flow

The order_index dictates display order on the case Tasks tab. Sequence tasks the way an analyst actually works the case:

1. Triage / scope (is this real? how big?)
2. Identify (who/what/where)
3. Investigate (logs, processes, network)
4. Decide (true positive / false positive / inconclusive)
5. Act (contain / notify / document)
6. Close (notify customer, retro)

Tasks higher in the list should be cheaper and faster — get to a triage decision early so the analyst doesn't burn 30 minutes investigating before realizing it's a known false positive.

### The two-template pattern: source + capability

Many investigations are "Wazuh detection that needs EDR follow-up". Rather than authoring one giant Wazuh-with-EDR template, use two:

- `Wazuh — Default` (auto-applies via source match)
- `CrowdStrike — Investigation` (manually layered when EDR work is needed)

Analyst flow:
1. Case auto-opens from Wazuh alert with the Wazuh template
2. Initial triage reveals lateral movement → analyst clicks "Apply template" and picks the CrowdStrike one
3. Both templates' tasks are now on the case, separately tracked

This keeps each template focused (and reusable for non-co-occurring scenarios) and lets you grow the library without exploding the matrix.

### Custom-task adds as a feedback loop

The "Add task" button on the case Tasks tab is for one-off needs that don't fit any template. But it's also a *signal*. If you find:

- The same custom task being added across many cases → promote to a template task
- A custom task being added on cases for one specific customer → maybe that customer needs an override template
- Custom tasks consistently appearing *before* the template's first task → reorder so the template starts where investigations actually start

Schedule a 30-minute monthly template review and look at recent custom tasks. The data is in the timeline (`task_added` events with `source: "custom"`).

### Timeline as compliance + handoff tool

The timeline is more than an audit log — it's the case's **narrative**. When you hand a case to another analyst (shift change, escalation), they should be able to read the timeline top-to-bottom and understand:

- What's been done
- What's left
- What the analyst was thinking (via task evidence comments and case Comments)

For compliance reviews, the timeline answers: "Was the procedure followed? When? By whom? If it wasn't, was the deviation documented?" The `forced=true` flag on close, the evidence comments on each task, and the actor/timestamp on each event give you that story without manually reconstructing it.

### Customer-portal as transparency tool

Customers see Tasks + Timeline read-only. Use this deliberately:

- **Mandatory tasks signal effort.** A customer seeing 5 mandatory tasks completed with evidence understands their alert was investigated, not just dismissed.
- **Status changes signal velocity.** OPEN → IN_PROGRESS → CLOSED with reasonable timestamps in the timeline shows responsiveness.
- **Evidence comments signal substance.** A task marked DONE with no evidence looks like a checkbox tick. A task with `"Pulled process tree from EDR, no suspicious children. See Velociraptor hunt vh-1234"` shows real work.

If you don't want the customer to see a particular detail, put it in the case Comments tab (still visible) framed as analyst-to-analyst conversation, or in your internal wiki and reference the link from the evidence comment.

### Quarterly template review checklist

Set a recurring 30-minute meeting with your analyst leads:

- [ ] What's the close-with-force rate per template? (Anything > 20% suggests a mandatory task is wrong.)
- [ ] What custom tasks were added this quarter? Any patterns?
- [ ] Are there customers consistently force-closing with the global template? Time for an override.
- [ ] Are there templates with > 80% NOT_NECESSARY on a specific task? Demote it.
- [ ] Have any new alert sources been onboarded that need their own template?
- [ ] Any guideline links that 404? (Wiki rot is real.)

---

## Common gotchas

### "I edited the template but the existing case didn't change"
Expected — task rows on a case are snapshots, not live references. New cases will pick up the edits; old ones won't.

### "I deleted a template and the case Tasks tab is empty"
Not expected. Template deletion preserves CaseTask snapshots and only nulls the soft `template_task_id` link. If tasks vanished, file an issue.

### "The wrong template auto-applied to my case"
Check the priority order. A more specific match (customer + source) always wins over a less specific one. If you have multiple defaults at the same scope, the most-recently-created wins — promote the one you want to default and the others get auto-demoted.

### "The customer portal shows a task they shouldn't see"
Customer portal scoping uses the case's `customer_code`. If a case is mis-scoped, the tasks follow it. Fix the case's customer_code; the tasks come along for the ride.
