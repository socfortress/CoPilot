# Customer Portal browser tests (Cypress)

They drive the real portal in a real browser against a **real backend and a real
MySQL**, seeded with known rows. Nothing below the UI is mocked; one spec edits a single
field of a real response to show a failed section.

## What they cover

| Spec | What it pins |
|---|---|
| `overview.cy.ts` | The Overview loads with **one** request (`/customer_portal/overview`) instead of the four it replaced, shows the seeded posture, recent alerts/cases and AI findings of the user's customer only, and a failing section does not blank the others. |
| `status-cards.cy.ts` | The Total / Open / In progress / Closed cards on the Alerts and Cases pages show the seeded counts (now from one grouped query per page). |
| `agents.cy.ts` | #1185 — the agents list loads one page from `/customer_portal/agents` (never the whole fleet), with server-side cards, status filter, a search sent once the user stops typing, and a CSV export of every filtered agent. |
| `alerts-list.cy.ts` | #1185 — the alerts list loads with one request, reacts to a filter within 250 ms (the old 400 ms debounce fails this), and the asset filter searches the server instead of downloading every asset name. |
| `ai-report.cy.ts` | #1185 — the Markdown renderer loads only when the full AI report opens; bundled languages are highlighted, others fall back to plain text instead of breaking the report. |
| `live-changes.cy.ts` | What an operator changes in CoPilot reaches the portal on the next page load: customer assignments, the AI report switch, branding (save, second save, removal). |

The same seed drives the API-level test `backend/tests/e2e/customer_portal_overview_e2e.py`,
which additionally checks field-by-field parity and the SQL statement budget.

## Running them

```bash
# once: the disposable e2e MySQL (never the one in .env)
docker run -d --name copilot-e2e-mysql -p 13306:3306 \
  -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \
  -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

# from customer-portal/
pnpm test:e2e        # headless
pnpm test:e2e:open   # Cypress UI
```

`scripts/e2e.sh` applies the migrations, starts the backend on `:5101` (without its
lifespan: no scheduler, MinIO or connector sync) and a portal dev server on `:3101`, runs
Cypress, then stops both. The backend log goes to a temp file whose path is printed when
a run fails. Ports, database and Python are overridable with `E2E_API_PORT`,
`E2E_WEB_PORT`, `E2E_MYSQL_URL`, `E2E_PYTHON`, … — deliberately not `MYSQL_*`, so a shell
pointed at a real CoPilot cannot be seeded by accident. The seed itself also refuses any
database that is not on port 13306 unless `E2E_ALLOW_ANY_DB=1`.

Selectors are `data-testid` attributes on the components, never CSS classes or copy.
