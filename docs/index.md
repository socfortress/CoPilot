# SOCFortress CoPilot Documentation

CoPilot is a **single pane of glass** for operating an open‑source SOC/SIEM stack (Wazuh, Graylog, Velociraptor, Grafana, etc.).

This documentation is organized into two tracks:

- **User Guide** (operators + admins/engineers)
- **Developer / AI Agent Docs** (architecture + safe change playbooks)

---

## Start here (pick your path)

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
- Every page is stored in‑repo under `docs/` so it can be updated via PRs.
