# Customer Portal browser tests (Cypress)

They drive the real portal in a real browser against a **real backend and a real
MySQL**, seeded with known rows. Nothing below the UI is mocked; one spec edits a single
field of a real response to show a failed section.

## What they cover

| Spec | What it pins |
|---|---|
| `overview.cy.ts` | The Overview loads with **one** request (`/customer_portal/overview`) instead of the four it replaced, shows the seeded posture, recent alerts/cases and AI findings of the user's customer only, and a failing section does not blank the others. |
| `status-cards.cy.ts` | The Total / Open / In progress / Waiting on you / Closed cards on the Alerts and Cases pages show the seeded counts (now from one grouped query per page). |
| `agents.cy.ts` | #1185 — the agents list loads one page from `/customer_portal/agents` (never the whole fleet), with server-side cards, status filter, a search sent once the user stops typing, and a CSV export of every filtered agent. |
| `agent-tabs.cy.ts` | #1256 — an agent's Vulnerabilities, SCA and Cases tabs: each loads when first opened. Vulnerabilities are counted per severity, worst first, filtered, searched, paged and exported (the CSV saved under the severity on screen). SCA lists the worst policy first and opens its checks failed first, with what to do about them and the policy's export. Cases are the agent's own customer's only, never another tenant's on the same host name. A tab that fails says so. Wazuh's answers come from `support/agent-findings.ts`, since the e2e backend has no Wazuh. |
| `event-search.cy.ts` | #1258 — event search's saved queries (saved under a name, kept across a reload, run again from the list; the same name updates, a deleted one is gone; a source removed since says so), recent searches (newest first, once each, clearable), the CSV export (the loaded events in the columns on screen, ISO UTC times, "load more" when some are left) and the column picker (per source, kept across a reload, used by the export, back to the SOC's layout). The indexer's answers come from `support/event-search.ts`, since the e2e backend has none; the tenancy of the same routes is `backend/tests/e2e/event_search_e2e.py`. |
| `alerts-list.cy.ts` | #1185 — the alerts list loads with one request, reacts to a filter within 250 ms (the old 400 ms debounce fails this), and the asset filter searches the server instead of downloading every asset name. Only the latest load counts: a slower, superseded filter never lands and the spinner stops (#1192). |
| `alert-filters.cy.ts` | #1245 — the alerts list's combined filters (title, status, source, asset, tags, creation dates) all in the URL: a shared link opens the same list with the controls filled in, a reload and the back button from an alert's page keep it, the status cards set the status and keep the rest, an empty result offers to clear, and an unreadable link shows the unfiltered list. Expectations come from the seed's `alert_rows`. Match the list's request with `support/alerts.ts:alertsListRequest`: a glob such as `alerts/filter?*` also matches `alerts/filter-options`. |
| `ai-report.cy.ts` | #1185 — the Markdown renderer loads only when the full AI report opens; bundled languages are highlighted, others fall back to plain text instead of breaking the report. |
| `ai-request.cy.ts` | #1215 — "Run AI analysis" on an alert's AI Report tab: offered only once the SOC allows it, confirmed before it is sent, the backend's refusal shown when the AI analyst cannot start, an accepted request followed in the tab, and a finished analysis offered again. |
| `cases-list.cy.ts` | #1185 — the cases list loads with one request and reacts to a filter within 250 ms. |
| `customer-filter.cy.ts` | #1185 — picking a customer in the global filter reloads the alerts, cases and agents lists and cards once, for that customer; changing a selection already set is covered too (the case a shallow watcher would miss if the store ever mutated its array in place). The alerts list's own filters and the global filter narrow together (#1245). |
| `customer-names.cy.ts` | #1243 — customers by name with the code beside it (global filter, found by name or code; Overview scope; alert; profile), the case/report/event-search forms seeded by one rule, and the list read live from `/customer_portal/me` rather than the token. |
| `navigation-abort.cy.ts` | Leaving a page aborts its in-flight reads (Overview → Alerts → Cases leaves only the Cases calls alive), while the page landed on, branding and a query-string change on the same page are left alone. |
| `alert-cases.cy.ts` | #1192 — an alert's Linked Cases tab: create a case from the alert, unlink it (the confirm closes at once, before the answer) and link it back. |
| `live-changes.cy.ts` | What an operator changes in CoPilot reaches the portal on the next page load: customer assignments, the AI report switch, branding (save, second save, removal). |
| `sla.cy.ts` | #1187 — the Service Levels page is offered only while the SOC publishes it for the customer, shows the seeded compliance, response times, open items and targets of the user's customer (never an analyst's name), links "waiting on you" to the filtered list, and a reply to a waiting alert hands it back. |
| `theme-switch.cy.ts` | #1192 — the toolbar theme switch flips between light and dark. |
| `profile.cy.ts` | #1192 — the profile page shows the user and both tabs; the never-shown image editor is gone. |

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
