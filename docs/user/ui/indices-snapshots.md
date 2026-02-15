---
title: Snapshot & restore (cold storage)
description: Offload old indexes into snapshot repositories and restore them later when needed.
---

# Snapshot & restore (cold storage)

**Menu:** Indices → Snapshot & Restore

**Best for:** Admin / Engineer

Snapshots let you **offload older indexes into cold storage** (snapshot repositories) so you can make room for new events while still keeping the ability to restore history later.

![Snapshot & Restore](../../assets/ui/indices-snapshots.png)

---

## When to use snapshots

Use snapshots when you need to:
- reduce disk usage on the indexer
- keep long-term historical logs without keeping them “hot”
- preserve data before major maintenance/changes

---

## Repository registration is required

CoPilot can manage snapshots, but the snapshot **repository must exist and be registered** in the Wazuh Indexer cluster first.

In the UI you’ll see this warning if none exist:

> “Snapshot repositories must be manually registered in your Wazuh Indexer cluster …”

![Repositories (placeholder)](../../assets/ui/indices-snapshots-repos.png)

---

## Step 1 — Verify repositories

1) Open **Indices → Snapshot & Restore**
2) Click **Repositories**
3) Confirm at least one repository exists and is healthy

---

## Step 2 — Create a snapshot

![Create snapshot (placeholder)](../../assets/ui/indices-snapshots-create-snapshot.png)

1) Go to **Snapshots**
2) Choose the repository
3) Select the index/index pattern(s) to snapshot
4) Run the snapshot

---

## Step 3 — Restore a snapshot (when you need old data)

![Restore snapshot (placeholder)](../../assets/ui/indices-snapshots-restore.png)

Restoring brings historical data back so you can:
- investigate an incident with older timelines
- run retro-hunts
- rebuild context for cases

---

## Step 4 — Schedule snapshots (automation)

![Scheduled snapshots (placeholder)](../../assets/ui/indices-snapshots-schedule.png)

If you regularly offload older logs, scheduled snapshots help keep disk usage stable.

---

## Common gotchas

### “No snapshot repositories found”
A repository must be registered in the Wazuh Indexer cluster before snapshots can run.

### “Snapshots succeed but disk is still full”
Snapshots don’t automatically delete hot indexes. You still need a retention plan:
- delete old indexes (with intent)
- reduce ingestion volume
- tune retention windows
