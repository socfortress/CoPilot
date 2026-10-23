# Mocked browser specs

Real app, real browser, stubbed backend.

The sibling suite in [`../e2e/`](../e2e/README.md) is about **tenancy** — what the server
refuses to send — so it insists on a live CoPilot and a live MySQL and seeds them before
it starts. Mocking there would happily "prove" a fix that does not exist.

These specs are the other kind: defects that live entirely in the browser. A link built
without a query parameter. A form that opens unfilled. The backend is scenery, and
pinning it at the network layer is what makes the scenario reproducible — the customer,
the alert, the asset and the event sources never move, so a failure means the app behaved
differently, not that the data did.

Everything above that line is real: the real Vue app, the real router, the real stores,
the real components, in a real Chromium.

```bash
pnpm test:e2e:mocked            # needs nothing running
pnpm test:e2e:mocked --headed   # watch it
pnpm exec playwright show-report
```

Vite is started by `playwright.mocked.config.ts` on port **5273** — a port of its own, so
an ordinary `pnpm dev` on 5173 is never reused (it proxies `/api` to whatever
`VITE_API_URL` said when *it* started, which is a confusing way to fail).

## What's here

| Spec | Issue |
|---|---|
| `event-search-source-prefill.spec.ts` | [#1124](https://github.com/socfortress/CoPilot/issues/1124) — "View in Event Search" does not carry the alert's source |
| `agent-velociraptor-id.spec.ts` | [#1217](https://github.com/socfortress/CoPilot/issues/1217) — saving an agent's Velociraptor ID ends on the edit icon with a success message, even when the spinner icon downloads slower than the save; a refused save says why |
| `ai-report-settings.spec.ts` | [#1215](https://github.com/socfortress/CoPilot/issues/1215) — an admin lets a customer's portal users request AI analyses and sets their daily limit; an analyst cannot |
| `customer-admins.spec.ts` | [#1296](https://github.com/socfortress/CoPilot/issues/1296) — on a customer's Security tab an admin makes a portal user a customer admin and disables and enables an account, each only once confirmed; a SOC user gets neither action |
| `responder-role.spec.ts` | [#1219](https://github.com/socfortress/CoPilot/issues/1219) — a responder is offered CoPilot Actions and the Command / Quarantine tabs and still no administration, an analyst is offered neither; an admin making someone a responder must pick their customers in the same step, sees a legacy analyst without customers flagged, and is offered no customer assignment for an admin |
| `uba-pages.spec.ts` | An incident alert raised by UBA links the UBA alert and entity pages, which link each other; back retraces them |
| `talon-v2-chat.spec.ts` | Talon v2 chat (talon-analyst M5-5): with the setting on, the AI Analyst chat tab lists threads with their customer, reads a thread's history back (a tool row, the approval card), streams a turn (the golden `v2_tool` stream), starts a general thread from the picker, says "waiting for a decision" on a 409 and locks a thread whose customer was removed; with it off, the v1 chat |
| `talon-v2-approvals.spec.ts` | Talon v2 chat action proposals (talon-analyst M5-11): a streamed turn proposes an alert status change, its card reads CoPilot's record (not the stream's arguments), the composer waits for the decision, the Approvals tab lists it with a count badge, the analyst approves, the card says executed, the badge goes, and the thread resumes once with an empty message |
| `talon-v2-cost.spec.ts` | Talon v2 cost and run views (talon-analyst M5-9): an admin sees the AI Analyst page's Usage and Budgets tabs, the usage total exactly as the API's decimal string; an analyst sees Usage with the non-admin note and, on a job's page, its cost and run timeline (an ERROR span marked), and no Budgets tab (nor any budgets request) |
| `talon-health.spec.ts` | The Talon health dashboard (the AI Analyst Overview tab): a degraded Talon shows every section (12 components by group, uptime rows, charts with "no data" for a series Talon doesn't record, the configuration), a fix expands, the 7 d window asks for `hours=168` and the cost chart opens the Usage tab; an unreachable Talon keeps CoPilot's checks with the reason; an older Talon gets the upgrade notice. `E2E_SHOTS=<dir>` saves a screenshot of each state |
| `waf-page.spec.ts` | WAF page: Events pages newest first with first / previous / next and a page-size picker, saying whether there is more (one extra row tells, since the WAF returns no total) and never showing a page count that grows, a row opens its detail; Threat intel is ranked by score, paged client-side and built without list elements; the requests chart uses the shared chart tooltip; the Overview's rank lists number their rows without list elements and keep "Events from this IP"; the header shows the selected WAF's state and facts; Blocks searches both lists by address or reason, and the WAF-managed list opens on a match there |

`mock-backend.ts` holds the fixture and the route table. Only the endpoints a flow
actually reads are described; everything else the app calls on the way falls through to a
permissive `{ success: true }` so the page still boots.

Two things to know before adding a spec:

- **Match `/api` on the pathname, not with a `**/api/**` glob.** In dev the app is served
  off the filesystem, so that glob also swallows the app's own `/src/api/*.ts` modules
  and the page never mounts at all.
- **Sign in through the form.** The session is AES-encrypted by `secure-ls` in storage
  and cannot be written from the test; `signIn()` lets the app build its own session out
  of a mocked `/auth/token` response, and the role comes from that token's `scopes`.
