/** What `tests/e2e/portal_overview_seed.py seed` prints: the rows every spec asserts against. */
export interface PortalSeed {
	customers: { a: string; b: string }
	portal_user: string
	portal_user_id: number
	admin: string
	password: string
	alerts: { a: StatusCounts; b: StatusCounts }
	cases: { a: StatusCounts; b: StatusCounts }
	agents_a: { total: number; online: number; critical: number; offline: number; statuses: string[]; os_list: string[] }
	/** The alert whose latest AI report carries the Markdown with code blocks. */
	ai_alert_id: number
	ai_a: { total_reports: number; severity_counts: Record<string, number> }
	/** Completed customer reports per customer. */
	reports: { a: number; b: number }
}

interface StatusCounts {
	total: number
	open: number
	in_progress: number
	closed: number
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
