import type { PortalSeed } from "../support/e2e"

/**
 * The global customer filter (#1185): picking a customer reloads each list and card once
 * for that customer. The watchers no longer walk the selection deeply; they react to the
 * store replacing it, and must still catch every change.
 */
describe("global customer filter", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
			// Two customers, so the filter is shown; granted before signing in because the
			// portal takes the list from the token.
			cy.adminApi(seed, "POST", `/auth/users/${seed.portal_user_id}/customers`, [seed.customers.a, seed.customers.b])
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed, `${seed.portal_user}-two-customers`)
	})

	after(() => {
		cy.adminApi(seed, "POST", `/auth/users/${seed.portal_user_id}/customers`, [seed.customers.a])
	})

	function pickCustomer(code: string) {
		cy.get("[data-testid=customer-filter]").click()
		cy.get(".n-base-select-option:visible").contains(code).click()
		cy.get("body").type("{esc}")
	}

	function expectCard(key: string, value: number) {
		cy.get(`[data-testid=stat-${key}] [data-testid=card-stats-value]`).should("have.text", String(value))
	}

	it("alerts: the cards and the list reload once for the picked customer", () => {
		cy.intercept("GET", "**/api/customer_portal/dashboard/alert-stats*").as("stats")
		cy.intercept("GET", "**/api/incidents/db_operations/alerts?*").as("list")
		cy.visit("/alerts")
		cy.wait(["@stats", "@list"])
		expectCard("total", seed.alerts.a.total + seed.alerts.b.total)

		pickCustomer(seed.customers.b)
		cy.wait("@stats").its("request.url").should("include", `customer_codes=${seed.customers.b}`)
		cy.wait("@list").its("request.url").should("include", `customer_codes=${seed.customers.b}`)
		expectCard("total", seed.alerts.b.total)
		cy.get("[data-testid=alerts-table] tbody tr").should("have.length", seed.alerts.b.total)

		// Changing a selection that is already set is the case a shallow watcher would miss
		// if the store ever mutated its array in place instead of replacing it.
		pickCustomer(seed.customers.a)
		cy.wait("@stats").its("request.url").should("include", `customer_codes=${seed.customers.a}`)
		cy.wait("@list")
		expectCard("total", seed.alerts.a.total + seed.alerts.b.total)

		cy.wait(800)
		cy.get("@stats.all").should("have.length", 3)
		cy.get("@list.all").should("have.length", 3)
	})

	it("cases: the cards and the list reload once for the picked customer", () => {
		cy.intercept("GET", "**/api/customer_portal/dashboard/case-stats*").as("stats")
		cy.intercept("GET", "**/api/incidents/db_operations/cases?*").as("list")
		cy.visit("/cases")
		cy.wait(["@stats", "@list"])

		pickCustomer(seed.customers.b)
		cy.wait("@stats").its("request.url").should("include", `customer_codes=${seed.customers.b}`)
		cy.wait("@list").its("request.url").should("include", `customer_codes=${seed.customers.b}`)
		expectCard("total", seed.cases.b.total)

		cy.wait(800)
		cy.get("@stats.all").should("have.length", 2)
		cy.get("@list.all").should("have.length", 2)
	})

	it("agents: one page request for the picked customer", () => {
		cy.intercept("GET", "**/api/customer_portal/agents?*").as("page")
		cy.visit("/agents")
		cy.wait("@page")

		pickCustomer(seed.customers.b)
		cy.wait("@page").its("request.url").should("include", `customer_codes=${seed.customers.b}`)
		expectCard("total", 1)

		cy.wait(800)
		cy.get("@page.all").should("have.length", 2)
	})
})
