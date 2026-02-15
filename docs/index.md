# SOCFortress CoPilot Documentation

<div class="sf-hero" markdown>

<div class="sf-hero-left" markdown>

## Operate your open‑source SOC

CoPilot is a **single pane of glass** for operating an open‑source SOC/SIEM stack (Wazuh, Graylog, Velociraptor, Grafana, Shuffle, and more).

<div class="sf-cta-row" markdown>

[Operator quickstart](user/operators-quickstart.md)
[Admin/Engineer quickstart](user/admins-quickstart.md)
[UI Reference (menu)](user/ui/overview.md)
[Developer docs](developer/start-here.md)

</div>

<div class="sf-hero-meta" markdown>

**Popular next steps:** [Customer provisioning](user/customer-provisioning.md) · [Videos (summarized)](user/videos.md) · [GitHub releases](https://github.com/socfortress/CoPilot/releases)

</div>

</div>

<div class="sf-hero-right" markdown>

<video class="sf-hero-video" autoPlay loop muted playsInline preload="auto">
  <source src="/assets/hero/copilot-hub.webm" type="video/webm" />
  <source src="/assets/hero/copilot-hub.mp4" type="video/mp4" />
</video>

</div>

</div>

---

## Choose your path

<div class="sf-home-grid" markdown>

<div class="sf-card" markdown>

### SOC operator / analyst

You live in **Incident Management** (alerts → cases → investigations).

- [Operator quickstart](user/operators-quickstart.md)
- [Incident Management UI guide](user/ui/incident-management.md)
- [Videos track (Operator)](user/videos.md#operator-track)

</div>

<div class="sf-card" markdown>

### Admin / engineer

You configure **sources, connectors, and integrations** so alerts flow into CoPilot.

- [Admin/Engineer quickstart](user/admins-quickstart.md)
- [External services + integrations](user/ui/external-services.md)
- [Videos track (Admin/Engineer)](user/videos.md#adminengineer-track)

</div>

<div class="sf-card" markdown>

### Developer / AI Agent

You’re changing the codebase, adding connectors, or debugging flows.

- [Start here](developer/start-here.md)
- [Architecture](architecture/ARCHITECTURE.md)
- [Data flows](architecture/DATA_FLOWS.md)
- [Database schema](architecture/DATABASE_SCHEMA.md)

</div>

<div class="sf-card" markdown>

### Video library (summarized)

Treat the YouTube playlist like documentation: links + structured bullets (no transcripts stored).

- [Browse videos](user/videos.md)
- [Role-based tracks](user/videos.md#jump-to-your-role)

</div>

</div>

---

## Popular tasks

<div class="sf-task-grid" markdown>

<div class="sf-task-card" markdown>

<h3 class="sf-task-title">Provision a customer</h3>

Create a tenant + set up the minimum required configuration.

[Customer provisioning →](user/customer-provisioning.md)

</div>

<div class="sf-task-card" markdown>

<h3 class="sf-task-title">Add integrations & connectors</h3>

Connect third‑party sources and external network connectors so data flows into CoPilot.

[Integrations overview →](user/ui/external-third-party-integrations.md)

</div>

<div class="sf-task-card" markdown>

<h3 class="sf-task-title">Triage an alert → open a case</h3>

Start from an alert, pivot to evidence, and manage work in a case.

[Incident alerts →](user/ui/incident-alerts.md)

</div>

<div class="sf-task-card" markdown>

<h3 class="sf-task-title">Manage indices</h3>

Find, validate, and troubleshoot index patterns and retention.

[Indices management →](user/ui/indices-management.md)

</div>

<div class="sf-task-card" markdown>

<h3 class="sf-task-title">Navigate the UI fast</h3>

Map the sidebar/menu to routes and learn deep‑link patterns.

[UI navigation guide →](user/navigation.md)

</div>

<div class="sf-task-card" markdown>

<h3 class="sf-task-title">Build / change CoPilot safely</h3>

Architecture, schema source‑of‑truth, and change playbooks.

[Developer start here →](developer/start-here.md)

</div>

</div>

---

## How to use this site

- Use the **left sidebar** (hamburger menu on mobile) to browse by area.
- Use **Search** (top bar) to jump straight to a topic.
- Everything lives under `docs/` and is updated via PRs (GitHub Pages build via Actions).
