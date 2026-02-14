# SOCFortress CoPilot Documentation

CoPilot is a **single pane of glass** for operating an open‑source SOC/SIEM stack (Wazuh, Graylog, Velociraptor, Grafana, Shuffle, etc.).

<video autoplay loop muted playsinline style="width:100%; border-radius:16px; margin: 12px 0 18px; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.02);">
  <source src="assets/hero/copilot-hub.webm" type="video/webm">
  <source src="assets/hero/copilot-hub.mp4" type="video/mp4">
</video>

<div class="sf-home-grid" markdown>

<div class="sf-card" markdown>

## New to CoPilot?

Start with the guides and get a working SOC workflow quickly.

[Getting started →](user/operators-quickstart.md){ .md-button .md-button--primary }

</div>

<div class="sf-card" markdown>

## Configure your stack

Admins/engineers: set up connectors + integrations so alerts flow.

[Admin quickstart →](user/admins-quickstart.md){ .md-button .md-button--primary }

</div>

<div class="sf-card" markdown>

## Developer / AI Agent Docs

Architecture, data flows, schema, and safe change playbooks.

[Start here →](developer/start-here.md){ .md-button }

</div>

<div class="sf-card" markdown>

## Video library (summarized)

Use the playlist like documentation: grouped summaries by topic.

[Browse videos →](user/videos.md){ .md-button }

</div>

</div>

---

## Pick your path

=== "SOC operator / analyst"

    You spend most of your time in **Incident Management** (alerts → cases → investigations).

    - [Quickstart (Operators)](user/operators-quickstart.md)
    - [User Guide Overview](user/overview.md)
    - [Videos (Playlist)](user/videos.md)

=== "Admin / engineer"

    You configure **connectors, sources, and integrations** so alerts flow into CoPilot.

    - [Quickstart (Admins/Engineers)](user/admins-quickstart.md)
    - [Features by Area](user/features.md)
    - [Videos (Playlist)](user/videos.md)

=== "Developer / AI Agent"

    You are making changes to the codebase, adding connectors, or debugging flows.

    - [Start Here](developer/start-here.md)
    - [Architecture](architecture/ARCHITECTURE.md)
    - [Data Flows](architecture/DATA_FLOWS.md)
    - [Database Schema](architecture/DATABASE_SCHEMA.md)

---

## How to use this site

- Use the **left sidebar** (hamburger menu on mobile) to navigate.
- Use **Search** (top bar) to jump straight to a topic.
- Everything lives under `docs/` and is updated via PRs.
