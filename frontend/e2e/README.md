# Browser end-to-end tests (Playwright)

These drive the real Vue app in a real Chromium against a **real backend and a real
MySQL**. Nothing is stubbed, on purpose: the tenancy behaviour they cover is entirely
about what the server refuses to send, and an API mock would happily "prove" a fix that
does not exist.

## What they cover

Issue [#1050](https://github.com/socfortress/CoPilot/issues/1050) and its follow-up
("logged in as analyst with one customer assigned, and I'm still able to see other
customer information"):

| Spec | What it pins |
|---|---|
| `customer-scoping.spec.ts` | An analyst assigned to one tenant sees one tenant — in the list, in the sidebar filter, on a typed-in URL, and at the API below the UI (including keys #1050 missed: customer *name*, agent id). |
| `unassigned-analyst.spec.ts` | An analyst with **no** assignment is still deployment-wide (the documented upgrade compromise) **and** is told so, since mistaking the sidebar filter for an assignment is what produced the follow-up report. |
| `admin-not-regressed.spec.ts` | The admin was not locked out — the failure mode a "deny everything" fix produces. |
| `global-filter-disclaimer.spec.ts` | The Customers page tells you the sidebar filter does not apply to it — but only while a customer is selected — and the list really is unchanged by it. |

## Running them

You need MySQL and the backend up; Vite is started by Playwright itself.

```bash
# 1. database
docker compose up -d copilot-mysql

# 2. backend (from the repo root)
cd backend && uvicorn copilot:app --port 5000

# 3. tests (from frontend/)
E2E_ADMIN_PASSWORD='<admin password>' pnpm test:e2e
```

The admin password is generated on the backend's **first boot** and printed only to its
log — search it for `Admin user password:`.

### Setting it once instead of every run

Copy `.env.e2e.example` to `.env.e2e` (gitignored) and fill in the admin credential:

```bash
cp .env.e2e.example .env.e2e
$EDITOR .env.e2e
pnpm test:e2e:ui       # no arguments needed from here on
```

Anything set on the command line still wins over the file, so a one-off
`E2E_API_URL=… pnpm test:e2e` keeps working.

### Two things that will waste your afternoon

**A `pnpm dev` you already had running.** Playwright reuses a dev server on the port it
wants, and Vite proxies `/api` to whatever `VITE_API_URL` said *when that server
started*. So the app under test can end up talking to a different CoPilot entirely —
every spec fails at sign-in for no visible reason. `global-setup.ts` detects exactly
this and tells you; the fix is either to stop that server or to run on your own port:

```bash
E2E_PORT=5199 pnpm test:e2e
```

**Port 5000 on macOS.** AirPlay Receiver binds it, so `uvicorn --port 5000` may look
like it started while requests reach AirPlay instead. Either turn AirPlay Receiver off
in *System Settings → General → AirDrop & Handoff*, or move the backend and point the
suite at it:

```bash
cd backend && uvicorn copilot:app --port 5001
VITE_API_URL=http://127.0.0.1:5001 E2E_API_URL=http://127.0.0.1:5001 pnpm test:e2e
```

### Watching it work

```bash
pnpm test:e2e:headed   # opens a real browser, slowed to 350ms/action so it is followable
pnpm test:e2e:ui       # Playwright UI: pick tests, step through, time-travel each action
pnpm test:e2e:debug    # step-by-step with the inspector and a live selector picker
pnpm test:e2e:report   # open the HTML report from the last run
```

`--headed` and `--debug` turn on slow motion automatically; override with
`E2E_SLOW_MO=800` (or `0` for full speed while still watching).

A failed run keeps a trace and a video — `pnpm test:e2e:report` and click the failed
test to replay it frame by frame.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `E2E_ADMIN_USER` | `admin` | Account used to seed customers and analysts |
| `E2E_ADMIN_PASSWORD` | `admin` | See above — almost always needs setting |
| `E2E_API_URL` | `http://127.0.0.1:5000` | Backend, for seeding and direct API assertions |
| `E2E_BASE_URL` | *(unset)* | Test an already-running frontend instead of starting Vite |
| `E2E_PORT` | `5173` | Port Playwright starts Vite on |
| `E2E_SLOW_MO` | `350` headed, `0` otherwise | Milliseconds between browser actions |

All of them can live in `.env.e2e` instead of the command line.

## Seeding

`e2e/seed.ts` creates two analysts and assigns one customer to one of them — all through
the public API as an admin, and idempotently, so reruns reuse what is there.
Deliberately not a DB fixture: *Users → Assign Customer* is itself part of what #1050
was about, so a broken assignment endpoint fails the suite instead of quietly producing
a "correctly" scoped analyst.

For the two tenants it tries to create `E2E_PWA` / `E2E_PWB`, but an **unlicensed**
CoPilot allows only one customer, so it falls back to two the deployment already has
(read-only — only the analysts it created are ever modified). Which two it settled on is
written to `e2e/.tenants.json` and read by the specs, since Playwright runs global setup
in its own process. With fewer than two customers in total it stops and says so.

The seeded users are prefixed `e2e_pw_` and are safe to leave in a dev database.
**Do not point this at a production deployment** — it creates users.
