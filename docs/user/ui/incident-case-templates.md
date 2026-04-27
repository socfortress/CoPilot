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

## Common gotchas

### "I edited the template but the existing case didn't change"
Expected — task rows on a case are snapshots, not live references. New cases will pick up the edits; old ones won't.

### "I deleted a template and the case Tasks tab is empty"
Not expected. Template deletion preserves CaseTask snapshots and only nulls the soft `template_task_id` link. If tasks vanished, file an issue.

### "The wrong template auto-applied to my case"
Check the priority order. A more specific match (customer + source) always wins over a less specific one. If you have multiple defaults at the same scope, the most-recently-created wins — promote the one you want to default and the others get auto-demoted.

### "The customer portal shows a task they shouldn't see"
Customer portal scoping uses the case's `customer_code`. If a case is mis-scoped, the tasks follow it. Fix the case's customer_code; the tasks come along for the ride.
