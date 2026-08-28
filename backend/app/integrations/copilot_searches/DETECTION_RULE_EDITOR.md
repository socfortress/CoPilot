# Detection Rule Editor, Validation & Backtest Engine — WORKING DOC

> Living scratch/tracker for branch `1093`. Not the final proposal — we edit this as we go.
> Status keys: ✅ done · 🚧 in progress · ⬜ todo · ❓ decision needed

---

## 1. What we're building
An in-app editor to **create/edit Graylog-only detection rules**, **validate** them (schema + query + live field checks), and **backtest** them against a tenant's real Graylog data before they go live — then **publish to GitHub** (PR/commit), never to a CoPilot database.

Scope = **Graylog-only** rules:
- top-level `graylog: { query: <string> }`
- optional top-level `aggregation:` block (placed **after** `graylog`, never nested)
- **no** `search:` (OpenSearch DSL) block, **no** `parameters:` block
- all validation/backtest goes through the **Graylog REST API** — OpenSearch is never queried directly.

## 2. Architecture decisions (locked / assumed)
- ✅ **Rules live in git, not a CoPilot DB.** The canonical catalog stays `socfortress/CoPilot-Search-Queries` (shared, read). Each client's **custom rules live in the client's own GitHub repo** (read + write). Both merge into the existing `RulesCache`, tagged by provenance (`catalog` vs `custom`).
- ✅ **The only CoPilot-side state is per-tenant config**, not rule content: custom-repo URL + a GitHub write token + the Graylog stream id (`customer_meta_graylog_stream` already exists).
- ✅ **Editor scope = Graylog-only** (per the format above). Existing dual-format catalog rules (with `search`) are not edited here.
- ❓ **ASSUMED (confirm): backtest run history is ephemeral** (cached by rule-hash + tenant + range), **no durable table**. Revisit if we want persistent run history.
- ❓ **ASSUMED (confirm): per-client GitHub access = PAT** stored in customer config for MVP; GitHub App is the cleaner long-term option.

## 3. Code-grounded facts (from the deep-dive)
- Rules are YAML pulled from GitHub into `RulesCache` (30-min TTL); **no create/edit path exists** — this feature adds it.
- Backtest engine: **Graylog *search* (`/api/search/messages`, `/api/search/aggregate`) is NOT wrapped yet** — net-new connector work. `/api/events/*` and `/api/streams/*` exist.
- Per-tenant Graylog stream: `customer_meta_graylog_stream` (customers model). ✅
- GitHub is **read-only** today (`GITHUB_TOKEN` for rate limits). Publish/PR = net-new (GitHub write API).
- Do **not** reuse `/copilot_searches/execute` — it queries the Wazuh **indexer** directly (wrong engine + GHSA-ch48-63px-6wp2 cross-tenant risk). Backtest is a **new Graylog-only path**.
- Deps present: `jsonschema 4.17.3`, `pyyaml` (backend); `vue-codemirror` + `@codemirror/*` (frontend).

## 4. Canonical rule shape (Graylog-only) — the linter target
Key order:
`name, id, version, schema_version, date, author, description, data_source, how_to_implement, known_false_positives, response, tags, graylog, aggregation`
- `name` str, `id` uuid str, `version` int, `schema_version` **quoted** str, `description` str (folded `>`)
- `graylog: { query: str }` — **only** `query`
- `response: { risk_score: int, severity: low|medium|high|critical }`
- `tags: { asset_type, mitre_attack_id: [..], custom_tags: [..], product: [..], security_domain }`
- `aggregation` (optional): `enabled` bool, `function` count|distinct_count, `field` (null for count, required for distinct_count), `group_by` [..], `window` "10m", `execute_every`, `threshold` int≥1, `condition` one of `> >= < <= ==`
- **forbidden:** `search`, `parameters`

## 5. Milestones & progress
1. ✅ **Linter package (L1 + L3)** + tests — `services/rule_linter.py`, 18 tests pass. *(schema via jsonschema + custom lints + Graylog query parse)*
2. ✅ **Graylog search calls** — `services/graylog_search.py` (`search_messages` / `search_aggregate` / `count_matches`). **Feature-local** (does NOT modify shared connector logic — reads connector config via the existing read-only helper and issues its own POST with `Accept: application/json`, since the tabular Search API defaults to CSV).
3. 🚧 **Editor UI + validate endpoint** — L1 + **L3 done & live**; L2 (reference integrity) todo. Save-as-draft todo. **Create-rule entry point + locked required fields done. Optional aggregation block now seeded in the template (unlocked).**
4. ⬜ **L4 field-existence** (per tenant, 3-outcome via Graylog message-search schema).
5. ✅ **Backtest — non-aggregation** (total via count aggregate, per-bucket sparkline, samples, top fields). Live end-to-end.
6. ✅ **Backtest — aggregation + threshold sensitivity** (local sliding-window simulation using the same `count`/`distinct_count` semantics the provisioner uses; estimated alerts, top offenders, threshold sensitivity). 8 unit tests pass.
7. ✅ **Publish → client GitHub (direct commit)** — `services/publish.py` + `POST /copilot_searches/publish` + editor `PublishModal`. Uses the per-tenant write token (MinIO); gated on lint-valid; create-or-update via Contents API. 5 unit tests. *(PR flow + upstream-contribution path still optional/later.)*
8. ✅ **Multi-repo RulesCache merge** — backend + frontend done; custom badge on cards + per-tenant config UI (Custom repos) + live-verified with `aminemoussaa/copilot-custom-rules-demo` → `local` (3 custom rules load, tagged). **Live publish verified by the user** (fine-grained PAT w/ Contents RW; rule "event id 1 + 11" round-tripped repo→card).
9. ✅ **Source filter** — `provenance` param on GET /copilot_searches (`catalog`|`custom`) + "Source" select in the grid filter popover (counts verified: 3050/4).
10. ❌ **Edit existing custom rule — built then REMOVED at the user's request** ("i don't like this feature"). All pieces reverted (card Edit button, editor `?rule=` loading + chip, PublishModal defaults). Updating a rule still works by publishing to the same path manually. Do not re-add without asking.
11. ✅ **Publish hardening** — `path` constrained to `detections/**.ya?ml` (no `..`/backslashes/other locations); **id-collision check** vs the cache (catalog or another custom file → clear error; re-publishing the same file → allowed as update). Verified live; 4 new tests (39 total).
12. ✅ **Custom-repo failure visibility** — `RulesCache.source_status` records per-repo fetch outcome each refresh; surfaced in `GET /custom-repos` (`last_refresh_ok/rules_loaded/last_refresh_error/last_refresh_at`) and as status chips in the Custom repos UI; plus `POST /custom-repos/test` dry-run + "Test" button (uses stored token when editing with blank field). Verified live (good repo → 4 rules; bad branch → clear error).
13. ⚠️ **Multi-tenant visibility scoping: deliberately SKIPPED per the user** ("keep it accessible to all") — every tenant's custom rules are visible to all authenticated users, including customer_user. Documented decision; revisit only if the user asks.
14. ✅ **L2 reference integrity** — folded into the linter as WARNINGS only (nothing valid becomes invalid): `$field$` message placeholders vs used fields, risk/threat_object fields vs used fields, MITRE id format, severity↔risk_score bands, quoted ISO date. 5 new tests (23 linter total).
15. ✅ **L4-lite field existence** — inside the backtest (customer already in scope): query/aggregation fields compared against the stream's real field population (`/api/views/fields`), returned as `missing_fields` + warning alert in the modal. Guarded (skipped when the stream has <5 fields, e.g. empty streams). Verified live: typo'd `eventlD` flagged for `local`.
16. ✅ **Draft auto-save** — editor YAML persisted to localStorage (600ms debounce), restored on mount with a toast; template buttons start fresh.
17. **Backend suite: 44 tests green** (9 publish + 3 custom-repo + 9 backtest + 23 linter).

## 6. Progress log
- _(init)_ Created working doc. Verified deps + wiring.
- **M1 done:** `services/rule_linter.py` (`lint_rule_yaml` / `lint_result`) — YAML parse, jsonschema structure, + custom lints: forbidden `search`/`parameters`, graylog-only-`query`, quoted `schema_version`, UUID id, canonical key order, aggregation-after-graylog, count/distinct_count↔field coupling, folded scalars, colon-quoting, recommended fields. 10 unit tests (`backend/tests/test_rule_linter.py`) pass.
- **M3 (L1 slice) done & live:** `POST /copilot_searches/validate` (admin/analyst) + `Api.copilotSearches.validateRule`. Editor at **`/copilot-searches/editor`** (`views/agents/CopilotSearchEditor.vue`): split-pane YAML + live (400ms-debounced) validation, seeded Graylog-only template w/ generated UUID, valid/error/warning status. `vue-tsc` clean.
- **Locked required-field editor:** upgraded the editor from a textarea to **CodeMirror** (`components/copilotSearches/RuleYamlEditor.vue`). Required-field keys (`name, id, version, schema_version, description, graylog, query`) are **highlighted** (tinted line + coloured bold key, light/dark aware) and **un-deletable** — a `transactionFilter` rejects any edit that would touch the `key:` token (values stay freely editable); attempting it fires a throttled "required field can't be removed" toast. `vue-tsc` clean; Vite HMR'd cleanly.
- **Create-rule entry point:** "Create rule" button in the Rules/Matrix tab bar suffix (`List.vue`) → routes to the editor (`name: CopilotSearchEditor`); editor gained a back button → `CopilotSearches`.
- **L3 query parse added to the linter** (`lint_graylog_query`): unbalanced quotes/parens/regex `/.../`, dangling boolean operators, leading-`.*`-regex perf warning. Folded into `/validate` (live in the editor). 8 more tests → **18 pass** total. Backend restarted; DB no-op ("already up to date").
- **Graylog syntax reference** in the editor: the right panel is now tabbed **Validation | Graylog syntax**. `components/copilotSearches/GraylogSyntaxReference.vue` is a condensed, restructured cheat-sheet of Graylog/Lucene search syntax (terms, phrases, AND/OR/NOT/+/-, fields + `_exists_`, grouping, wildcards, fuzzy, proximity, ranges, regex, escaping, examples, gotchas) with a link to the official docs. `vue-tsc` clean.
- **M2 + M5 + M6 done — Backtest engine (Graylog-only), feature-local:**
  - `services/graylog_search.py` — `search_messages`/`search_aggregate`/`count_matches` via Graylog's tabular Search API, forcing `Accept: application/json`. Self-contained: reads connector config with the existing read-only helper; **no change to shared connector logic** (per user: "only update the copilot searches area, don't modify the app logic").
  - `services/backtest.py` — `run_backtest(yaml, customer_code, range_seconds)`: resolves the tenant stream (`customer_meta_graylog_stream`), guards against placeholder streams (must be a 24-hex ObjectId), fetches matching events once via `/api/search/messages` (cap 10k), and computes **everything locally**: total, per-bucket sparkline, samples, top-value breakdown, and — for aggregation rules — a **sliding-window threshold simulation** (estimated alerts, top offenders, threshold sensitivity) using the same `count`/`distinct_count` semantics as `_build_aggregation_series_and_conditions`. Graceful errors; total is a lower bound (labelled) only when the 10k cap is hit. *(The `/api/search/aggregate` endpoint proved fragile on live Graylog — rejects empty group_by, needs keyword fields — so the backtest is messages-only.)*
  - `POST /api/copilot_searches/backtest` (admin/analyst), schema `BacktestRequest/Response`. `tests/test_backtest_logic.py` — 7 tests pass (window/timestamp parse, sparkline, top fields, count + distinct_count sims, bad-window guard). Route smoke-tested (401 unauth).
  - Frontend: `components/copilotSearches/BacktestModal.vue` (customer picker + look-back range + results: headline stats, CSS sparkline, aggregation panel, top values, sample table). Wired into the editor — **Backtest button enabled**. `Api.copilotSearches.backtestRule` + types added. `vue-tsc` clean.
- **Template gained an optional `aggregation:` block** (`enabled: false`, count/field/group_by/window/threshold/condition) — present but **unlocked** (not in `PROTECTED_KEYS`), so it guides threshold rules without forcing it on simple ones. Validates green.
- **Mock test data + design polish pass (all copilot-searches only):**
  - Injected 56 benign mock Sysmon (eventID 1) events into the `local` tenant's Graylog stream via GELF HTTP (routed by `agent_labels_customer=local`), incl. a 35-event "alice" burst so the aggregation path fires. Tagged `backtest_mock=true`. (Dev-only helper; `00001`/`test` streams are placeholders, `crowd`/`graylogtest` indices are broken.)
  - **Full-event inspector**: sample rows are clickable → modal showing the complete event. Backend pulls the per-stream field set (`POST /api/views/fields`) for the ~20 sample events (bounded 2nd fetch, absent `-` values filtered). Inspector has a field filter, click-to-copy values, collapsible `gl2_*` internals, Copy JSON.
  - **Backtest modal redesign** with app primitives: `CardStats`+`CardStatsIcon` tiles, `ChartColumn` (echarts) sparkline (ISO bucket labels), proportion bars for top values + offenders, sensitivity chip row.
  - **Editor polish**: template menu (Simple vs Rule-with-aggregation), Copy YAML, validation panel grouped into Errors/Warnings with a valid hero; findings are **clickable → jump to the offending line** (RuleYamlEditor exposes `goToLine()` with a transient flash).
  - **Graylog syntax reference**: filter box + click-to-copy examples.
  - `vue-tsc` clean; all HMR'd clean. No shared-app files touched.
- **M8 (backend) — Multi-repo custom rules read/merge (decision: MinIO, per-tenant):**
  - `services/custom_repos.py` — per-tenant pointer `{repo, branch, token?, enabled}` in MinIO bucket `copilot-searches`, key `custom-repos/<customer_code>.json` (reuses infra; no DB change). CRUD + `redact()` (token never returned, only `has_token`). Round-trip verified vs live MinIO (`10.255.255.5`).
  - `RulesCache` refactored to pull the **canonical catalog + every enabled custom repo** the same way (tree+raw). Rules tagged `_provenance` (catalog|custom) + `_owner_customer_code`; catalog fetched first and **wins id collisions** (dupes skipped + logged). No regression: canonical still loads 3050 rules. `_custom_repo_headers()` uses the client's read token or falls back to `GITHUB_TOKEN`.
  - `provenance` + `owner_customer_code` added to `RuleSummary`/`RuleDetail` (so cards can badge).
  - Endpoints `GET/PUT/DELETE /copilot_searches/custom-repos[/{customer_code}]` (admin/analyst). Refresh endpoint re-pulls everything.
  - Tests `tests/test_custom_repos.py` (3): merge+tag+collision, per-file tagging (custom + catalog). All green.
  - **TODO (frontend):** "Custom" badge on rule cards (read `provenance`), per-tenant config UI (customer picker + repo/branch/token, save/delete, then Refresh). **Multi-tenant scoping** of which custom rules a `customer_user` sees is still open (today all provenance shown to admin/analyst) — tighten before prod.

## 7. Endpoints
- ✅ `POST /copilot_searches/validate` — L1+L3 lint of a YAML string → findings.
- ✅ `POST /copilot_searches/backtest` — synchronous, Graylog-only. Body `{yaml, customer_code, range_seconds}` → total/sparkline/samples/top_fields (+ aggregation sim). *(Sync for now; promote to a background job only if large-window runs get slow.)*
- `POST /copilot_searches/publish` — open PR/commit to the target repo. *(later)*

## 8. Open questions
- Confirm decisions in §2 (backtest history ephemeral? PAT vs GitHub App?).
- Which repo does "publish" default to — client's custom repo, with an opt-in "contribute upstream" PR to the canonical repo?
- Do we need per-rule enable/disable state now, or is that the separate deployment-state feature (out of scope)?
