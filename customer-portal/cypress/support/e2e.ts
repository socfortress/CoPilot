/** What `tests/e2e/portal_overview_seed.py seed` prints: the rows every spec asserts against. */
export interface PortalSeed {
	customers: { a: string; b: string }
	/** Their names, deliberately unlike the codes (#1243). */
	customer_names: { a: string; b: string }
	portal_user: string
	portal_user_id: number
	admin: string
	password: string
	alerts: { a: StatusCounts; b: StatusCounts }
	/** Every seeded alert, oldest first, with what the list's filters read (#1245). */
	alert_rows: { a: AlertRow[]; b: AlertRow[] }
	alert_tags: { phishing: string; vip: string }
	cases: { a: StatusCounts; b: StatusCounts }
	agents_a: { total: number; online: number; critical: number; offline: number; statuses: string[]; os_list: string[] }
	/** The alert whose latest AI report carries the Markdown with code blocks. */
	ai_alert_id: number
	/** An open alert of A that no AI analysis ever ran on (#1215). */
	fresh_alert_id: number
	/** An open alert of A with no AI analysis, for an investigation a test runs itself (#1273). */
	ai_idle_alert_id: number
	/** An alert of A in A's first case (`agent_a0.case_id`), which is open (#1305). */
	cased_alert_id: number
	ai_a: { total_reports: number; severity_counts: Record<string, number> }
	/** Completed customer reports per customer. */
	reports: { a: number; b: number }
	/** What the SLA page must show for customer A (#1187). */
	sla_a: SlaSeed
	/** What the Overview's trend counts for customer A, over 7 days as over 30 (#1273). */
	trend_a: {
		alerts_opened: number
		alerts_closed: number
		cases_opened: number
		cases_closed: number
		/** Still open now (all of A's clocks start inside the window). */
		alerts_open: number
		cases_open: number
	}
	/** A's first agent and its case (#1256); B's case names the same host and must not show. */
	agent_a0: { agent_id: string; hostname: string; case_id: number }
	agent_b0_id: string
	foreign_case_id: number
	/** The alert and case of A that wait on the customer (PENDING_CUSTOMER). */
	waiting_alert_id: number
	waiting_case_id: number
}

export interface AlertRow {
	name: string
	status: string
	source: string
	/** The calendar day it was created on, `YYYY-MM-DD` (noon UTC: the same day in any timezone). */
	day: string
	tags: string[]
	assets: string[]
}

interface SlaSeed {
	alerts_opened: number
	ack_met: number
	ack_breached: number
	ack_rate: number
	resolve_rate: number
	open_alerts: number
	open_cases: number
	waiting_on_you: number
}

interface StatusCounts {
	total: number
	open: number
	in_progress: number
	closed: number
	pending_customer: number
}

declare global {
	// eslint-disable-next-line ts/no-namespace
	namespace Cypress {
		interface Chainable {
			/** Re-seed the e2e database (idempotent) and expose the result as `@seed`. */
			seedPortal: () => Chainable<PortalSeed>
			/**
			 * Sign in through the real login form; cached per `sessionKey` across specs. Use a
			 * distinct key after changing the user's customers: the portal reads them from the
			 * token issued at login.
			 */
			loginToPortal: (seed: PortalSeed, sessionKey?: string) => Chainable<void>
			/** Call the backend as the seeded admin, e.g. to change what the portal user may see. */
			adminApi: (
				seed: PortalSeed,
				method: string,
				path: string,
				body?: RequestBody
			) => Chainable<Response<unknown>>
		}
	}
}

// A browser notice, not an application error: ResizeObserver could not deliver every
// notification in one frame (naive-ui's autosizing textarea inside an animated tab).
Cypress.on("uncaught:exception", err => !err.message.includes("ResizeObserver loop"))

Cypress.Commands.add("seedPortal", () => {
	return cy.task<PortalSeed>("portal:seed", null, { timeout: 60000 }).then(seed => {
		cy.wrap(seed).as("seed")
		return cy.wrap(seed)
	})
})

Cypress.Commands.add("loginToPortal", (seed, sessionKey = seed.portal_user) => {
	cy.session(sessionKey, () => {
		cy.visit("/login")
		cy.get("[data-testid=login-username] input").type(seed.portal_user)
		cy.get("[data-testid=login-password] input").type(seed.password, { log: false })
		cy.get("[data-testid=login-submit]").click()
		cy.location("pathname").should("not.eq", "/login")
	})
})

let adminToken: string | null = null

Cypress.Commands.add("adminApi", (seed, method, path, body) => {
	const send = (token: string) =>
		cy.request({ method, url: `/api${path}`, body, headers: { Authorization: `Bearer ${token}` } })

	if (adminToken) return send(adminToken)

	return cy
		.request({
			method: "POST",
			url: "/api/auth/token",
			form: true,
			body: { username: seed.admin, password: seed.password }
		})
		.then(response => {
			adminToken = response.body.access_token as string
			return send(adminToken)
		})
})

export {}
