import type { PortalSeed } from "../support/e2e"

/**
 * The status cards on the Alerts and Cases pages (#1181): the counts now come from one
 * grouped query per page and must still be the seeded ones, per status.
 */
describe("status cards", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	function expectCards(counts: PortalSeed["alerts"]["a"]) {
		for (const key of ["total", "open", "in_progress", "closed"] as const) {
			cy.get(`[data-testid=stat-${key}] [data-testid=card-stats-value]`).should("have.text", String(counts[key]))
		}
	}

	it("alerts: total, open, in progress, closed", () => {
		cy.intercept("GET", "**/api/customer_portal/dashboard/alert-stats*").as("stats")
		cy.visit("/alerts")
		cy.wait("@stats")
		expectCards(seed.alerts.a)
	})

	it("cases: total, open, in progress, closed", () => {
		cy.intercept("GET", "**/api/customer_portal/dashboard/case-stats*").as("stats")
		cy.visit("/cases")
		cy.wait("@stats")
		expectCards(seed.cases.a)
	})
})
