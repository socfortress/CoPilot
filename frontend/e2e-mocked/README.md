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
