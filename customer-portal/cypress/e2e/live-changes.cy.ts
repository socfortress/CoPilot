import type { PortalSeed } from "../support/e2e"

/**
 * What an operator changes in CoPilot reaches the portal on the next page load (#1181):
 * the per-request memo of accessible customers and the in-process branding cache must
 * never serve an answer from before the write.
 */
describe("changes made in CoPilot", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	after(() => {
		// Leave the seed as the other specs expect it, whatever failed above.
		cy.adminApi(seed, "POST", `/auth/users/${seed.portal_user_id}/customers`, [seed.customers.a])
		cy.adminApi(seed, "PUT", `/customer_portal/ai_reports/settings/${seed.customers.a}`, { enabled: true })
		cy.adminApi(seed, "DELETE", `/customer_portal/branding/${seed.customers.a}`)
	})

	function alertsTotal() {
		return cy.get("[data-testid=posture-alerts] [data-testid=posture-footnote]")
	}

	it("a customer assigned to the user shows up at once", () => {
		cy.adminApi(seed, "POST", `/auth/users/${seed.portal_user_id}/customers`, [seed.customers.a, seed.customers.b])
		cy.visit("/overview")
		alertsTotal().should("have.text", `${seed.alerts.a.total + seed.alerts.b.total} total`)
		cy.get("[data-testid=recent-alerts]").should("contain", seed.customers.b)

		cy.adminApi(seed, "POST", `/auth/users/${seed.portal_user_id}/customers`, [seed.customers.a])
		cy.reload()
		alertsTotal().should("have.text", `${seed.alerts.a.total} total`)
		cy.get("[data-testid=recent-alerts]").should("not.contain", seed.customers.b)
	})

	it("turning the AI report switch off hides the findings, on shows them again", () => {
		cy.intercept("GET", "**/api/customer_portal/overview*").as("overview")

		cy.adminApi(seed, "PUT", `/customer_portal/ai_reports/settings/${seed.customers.a}`, { enabled: false })
		cy.visit("/overview")
		cy.wait("@overview")
		alertsTotal().should("have.text", `${seed.alerts.a.total} total`)
		cy.get("[data-testid=ai-findings]").should("not.exist")

		cy.adminApi(seed, "PUT", `/customer_portal/ai_reports/settings/${seed.customers.a}`, { enabled: true })
		cy.reload()
		cy.wait("@overview")
		cy.get("[data-testid=ai-findings]").should("contain", "High finding")
	})

	it("saved branding is shown at once, and so is its removal", () => {
		cy.adminApi(seed, "PUT", `/customer_portal/branding/${seed.customers.a}`, {
			enabled: true,
			title: "Cypress Branding"
		})
		cy.visit("/overview")
		cy.title().should("eq", "Cypress Branding")
		cy.get("footer").should("contain", "Cypress Branding")

		// A second save straight after the first: a cache that was not invalidated
		// would keep serving "Cypress Branding" for its whole TTL.
		cy.adminApi(seed, "PUT", `/customer_portal/branding/${seed.customers.a}`, {
			enabled: true,
			title: "Cypress Branding 2"
		})
		cy.reload()
		cy.title().should("eq", "Cypress Branding 2")

		cy.adminApi(seed, "DELETE", `/customer_portal/branding/${seed.customers.a}`)
		cy.reload()
		cy.get("footer").should("not.contain", "Cypress Branding")
	})
})
