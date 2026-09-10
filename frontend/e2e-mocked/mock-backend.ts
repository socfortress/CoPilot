import type { BrowserContext, Page, Route } from "@playwright/test"
import { Buffer } from "node:buffer"
import { expect } from "@playwright/test"

/**
 * A fixed CoPilot deployment, served to the browser at the network layer.
 *
 * Only the handful of endpoints the flow under test actually reads are described; every
 * other call the app makes on the way (licence gating, health checks, sidebar context,
 * …) falls through to a permissive default so the page still boots. The goal is not a
 * backend simulator — it is a stable stage for one navigation.
 */

const CUSTOMER_CODE = "ACME"

/**
 * The alert's asset. `index_name` is the concrete index the alert was read from, and it
 * is the only handle the asset carries back to the source that produced it: it matches
 * the `office365` event source's `index_pattern`, not the Wazuh one.
 */
export const ASSET = {
	id: 42,
	agent_id: "001",
	alert_context_id: 7,
	alert_linked: 1234,
	asset_name: "WIN-DC01",
	customer_code: CUSTOMER_CODE,
	index_id: "abc123def456",
	index_name: "office365-acme-2026.09.08",
	velociraptor_id: "C.1234567890abcdef"
}

export const ALERT_ID = 99

/** The event source the alert came from — what the analyst has to pick by hand today. */
export const EXPECTED_SOURCE_NAME = "Office 365 Audit"

/**
 * Two enabled sources, and the alert's is NOT the EDR one.
 *
 * That combination is the whole point of the fixture. Event Search, handed a link with
 * no source, falls back to "first enabled EDR source" — so with a Wazuh-only customer
 * the omission is invisible and the bug looks fixed. Real deployments run several
 * sources per customer, which is where the missing parameter starts costing clicks.
 */
export const EVENT_SOURCES = [
	{
		id: 1,
		customer_code: CUSTOMER_CODE,
		name: "Wazuh EDR",
		index_pattern: "wazuh-alerts-*",
		event_type: "EDR",
		time_field: "timestamp",
		enabled: true,
		displayed_columns: null,
		created_at: "2026-01-01T00:00:00Z",
		updated_at: "2026-01-01T00:00:00Z"
	},
	{
		id: 2,
		customer_code: CUSTOMER_CODE,
		name: EXPECTED_SOURCE_NAME,
		index_pattern: "office365-acme-*",
		event_type: "Cloud Integration",
		time_field: "timestamp",
		enabled: true,
		displayed_columns: null,
		created_at: "2026-01-01T00:00:00Z",
		updated_at: "2026-01-01T00:00:00Z"
	}
]

const CUSTOMERS = [{ customer_code: CUSTOMER_CODE, customer_name: "Acme Corp" }]

/** How the filter bar labels an option, and so what a selected source reads as on screen. */
export function sourceOptionLabel(name: string) {
	const source = EVENT_SOURCES.find(s => s.name === name)
	return `${name} (${source?.event_type})`
}

/** The source the "first enabled EDR source" fallback lands on instead. */
export const FALLBACK_SOURCE_NAME = "Wazuh EDR"

const ALERT = {
	id: ALERT_ID,
	alert_creation_time: "2026-09-08T10:00:00Z",
	alert_description: "Suspicious mailbox rule created",
	alert_name: "Office 365 — suspicious inbox rule",
	assigned_to: null,
	customer_code: CUSTOMER_CODE,
	source: "office365",
	status: "OPEN",
	time_closed: null,
	comments: [],
	assets: [ASSET],
	tags: [],
	linked_cases: [],
	iocs: [],
	verdict: null,
	verdict_reason: null,
	verdict_note: null,
	verdict_by: null,
	verdict_at: null
}

const ALERT_CONTEXT = {
	id: ASSET.alert_context_id,
	source: "office365",
	context: { process_name: [], rule_id: "60123" }
}

function json(route: Route, body: unknown, status = 200) {
	return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) })
}

/** A structurally valid JWT. The app decodes it without verifying — see `stores/auth.ts`. */
function mintToken(username: string, scopes: string[]) {
	const b64 = (o: object) =>
		Buffer.from(JSON.stringify(o))
			.toString("base64")
			.replace(/\+/g, "-")
			.replace(/\//g, "_")
			.replace(/=+$/, "")

	// Far enough out that the client's proactive-refresh window (1h) never opens.
	const exp = Math.floor(Date.now() / 1000) + 60 * 60 * 24
	return `${b64({ alg: "HS256", typ: "JWT" })}.${b64({ sub: username, scopes, exp })}.e2e-mocked-not-a-signature`
}

export async function installMockBackend(context: BrowserContext) {
	// Matched on the pathname rather than with a `**/api/**` glob: in dev the app is
	// served straight off the filesystem, so that glob also swallows the app's own
	// `/src/api/*.ts` modules and the page never boots.
	await context.route(
		url => url.pathname.startsWith("/api/"),
		async route => {
			const path = new URL(route.request().url()).pathname.replace(/^\/api/, "")

			if (path === "/auth/token" || path === "/auth/refresh") {
				return json(route, {
					success: true,
					access_token: mintToken("admin", ["admin"]),
					token_type: "bearer"
				})
			}
			if (path === "/customers") {
				return json(route, { success: true, customers: CUSTOMERS })
			}
			if (path === `/incidents/db_operations/alert/${ALERT_ID}`) {
				return json(route, { success: true, alerts: [ALERT] })
			}
			if (path === `/incidents/db_operations/alert/context/${ASSET.alert_context_id}`) {
				return json(route, { success: true, alert_context: ALERT_CONTEXT })
			}
			if (path === `/siem/event_sources/${CUSTOMER_CODE}`) {
				return json(route, { success: true, event_sources: EVENT_SOURCES })
			}
			if (/^\/siem\/events\/[^/]+\/[^/]+\/fields$/.test(path)) {
				return json(route, {
					success: true,
					fields: [{ field: "user_id", type: "keyword" }],
					total: 1,
					index_pattern: "*"
				})
			}
			if (path.startsWith("/siem/events/")) {
				return json(route, { success: true, events: [], total: 0, scroll_id: null })
			}

			// Everything else: enough of a response that the app renders an empty state
			// rather than an error toast, and nothing the assertions depend on.
			return json(route, { success: true, message: "mocked" })
		}
	)
}

/**
 * Signs in through the real login form.
 *
 * The role the app grants comes from the JWT's `scopes`, which the mock issues — so the
 * session is the one the app built for itself out of a server response, not a token
 * planted in storage (which is AES-encrypted by secure-ls and not writable from here).
 */
export async function signIn(page: Page) {
	await page.goto("/login")

	// Generous: the first navigation of a run pays for Vite's cold compile of the whole
	// app, which is far slower than anything the tests themselves do.
	const username = page.getByPlaceholder("Insert your username")
	await expect(username).toBeVisible({ timeout: 90_000 })

	await username.fill("admin")
	await page.getByPlaceholder("Insert your password").fill("whatever")
	await page.getByRole("button", { name: /sign in with password/i }).click()
	await expect(page).toHaveURL(/\/overview/, { timeout: 60_000 })
}
