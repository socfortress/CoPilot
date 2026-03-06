---
title: Tag-Based Access Control (Tag RBAC)
description: Restrict which alerts users and roles can see based on assigned tags.
---

**Menu:** Users → (select user) → Assign Tags | Settings → Tag RBAC Settings

**Best for:** Admin

Tag RBAC lets admins **restrict which alerts a user can see** based on the tags applied to those alerts. This is useful in multi-team or MSSP environments where different analysts should only see alerts relevant to their scope.

---

## How it works (mental model)

1. Alerts in Incident Management can be **tagged** (e.g., `Network`, `Endpoint`, `O365`, `CustomerA`).
2. An admin **assigns one or more tags** to a user (or role).
3. When Tag RBAC is **enabled**, that user only sees alerts matching their assigned tags.

```
┌──────────────┐         ┌─────────────────┐
│   Alert      │         │   Analyst       │
│  tags:       │         │  assigned tags: │
│  [Network]   │◄────────│  [Network]      │  ✅ Can see
│  [Endpoint]  │         │                 │
└──────────────┘         └─────────────────┘

┌──────────────┐         ┌─────────────────┐
│   Alert      │         │   Analyst       │
│  tags:       │         │  assigned tags: │
│  [O365]      │    ✖    │  [Network]      │  ❌ Cannot see
└──────────────┘         └─────────────────┘
```

> **Key rule:** A user with **no tags assigned** has **no restrictions** — they can see all alerts. Tag RBAC only restricts visibility once you assign specific tags to a user.

---

## Access rules summary

| User configuration | What they see |
|---|---|
| **No tags assigned** | All alerts (unrestricted) |
| **Tags assigned** (e.g., `Network`, `Endpoint`) | Only alerts tagged with `Network` or `Endpoint` |
| **Admin role** | Always full access regardless of tag assignments |
| **Scheduler role** | Always full access regardless of tag assignments |

---

## Enabling Tag RBAC

1. Navigate to **Settings → Tag RBAC Settings** (admin only).
2. Toggle **Enable Tag RBAC** to **On**.
3. Configure how **untagged alerts** should be handled (see below).
4. Click **Save Settings**.

> Until Tag RBAC is enabled, tag assignments on users have no effect — all users can see all alerts.

---

## Untagged alert behavior

When Tag RBAC is enabled, you need to decide what happens to alerts that **don't have any tags**. There are three options:

| Option | Behavior |
|---|---|
| **Visible to All** | Every user can see untagged alerts, regardless of their tag assignments. This is the safest default. |
| **Admin Only** | Only admin users can see untagged alerts. Restricted users won't see them. |
| **Default Tag** | Untagged alerts are treated as if they have a specific tag you choose. Users assigned that tag will see untagged alerts. |

### When to use "Default Tag"

This is useful when you want a catch-all group. For example:

- Create a tag called `General` or `Triage`.
- Set it as the default tag.
- Assign `General` to your triage team.
- Now untagged alerts land in their queue automatically without needing to tag every single alert.

---

## Assigning tags to users

1. Navigate to the **Users** page.
2. Select the user you want to configure.
3. In the user detail panel, find the **Assign Tags** section.
4. Use the multi-select dropdown to choose one or more tags.
5. Click **Save**.

To give a user unrestricted access again, clear all assigned tags (use **Clear All**) and save.

> Tags must already exist in the system (created via alert tagging in Incident Management). You cannot create new tags from the assignment panel.

---

## Assigning tags to roles

Instead of assigning tags per-user, you can assign tags at the **role** level. This is useful when all users with a particular role should have the same alert visibility.

- **Role-level tags** apply to every user with that role.
- **User-level tags** override or extend role-level tags for individual users.
- If a user has both role-level and user-level tags, they see alerts matching **any** of their combined tags.

---

## Checking effective access

You can verify what a user actually has access to by viewing their **effective access**, which combines:

- Their role's tag assignments
- Their personal tag assignments
- Customer access restrictions (if applicable)

This is helpful for troubleshooting when a user reports they can't see expected alerts.

---

## Common scenarios

### MSSP with multiple customers

| Tag | Assigned to |
|---|---|
| `CustomerA` | Analyst 1, Analyst 2 |
| `CustomerB` | Analyst 3 |
| `CustomerA`, `CustomerB` | Senior Analyst (sees both) |

Each analyst only sees alerts tagged with their customer. The senior analyst sees both.

### SOC with specialized teams

| Tag | Assigned to |
|---|---|
| `Network` | Network team |
| `Endpoint` | Endpoint team |
| `O365` | Cloud team |

Alerts are tagged by source, and each team only sees their relevant alerts.

### Unrestricted senior staff

Leave the tag assignment **empty** for senior analysts or SOC leads. They'll have full visibility across all alerts without restrictions.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| User can't see any alerts | Tag RBAC is enabled but user has tags assigned and no alerts match | Verify the user's assigned tags match tags actually applied to alerts |
| User sees all alerts despite having tags | Tag RBAC is not enabled | Enable Tag RBAC in Settings → Tag RBAC Settings |
| Untagged alerts are invisible to analysts | Untagged alert behavior set to "Admin Only" | Change to "Visible to All" or "Default Tag" |
| New alerts aren't visible to restricted user | New alerts aren't tagged yet | Tag the alerts, or set a default tag so untagged alerts route to the right users |

---

## Related pages

- [Incident Alerts](./incident-alerts.md)
- [Incident Cases](./incident-cases.md)
- [Graylog Management (detections)](./graylog-management.md)
