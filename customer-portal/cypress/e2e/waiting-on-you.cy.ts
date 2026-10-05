import type { PortalSeed } from "../support/e2e"

/**
 * "Waiting on you" in the lists (#1187): the stats card counts what the SOC is waiting on
 * the customer for, filtering the list on that status shows exactly those items, and the
 * customer can see the status but never pick it — it is the SOC's to set.
 *
 * UI assertions only: whether the backend also refuses the status from a portal user is
 * the backend's own test.
 */
describe("waiting on you", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	function filterOnWaiting(list: "alerts" | "cases") {
		cy.get(`[data-testid=${list}-filter-key]`).click()
		cy.get(".n-base-select-option:visible").contains(/^statuses$/).click()
		cy.get(`[data-testid=${list}-filter-value]`).click()
		cy.get(".n-base-select-option:visible").contains(/^Waiting on you$/).click()
	}

	for (const list of ["alerts", "cases"] as const) {
		it(`${list}: the card's count is exactly what the list shows filtered on that status`, () => {
			const stats = list === "alerts" ? "alert-stats" : "case-stats"
			cy.intercept("GET", `**/api/customer_portal/dashboard/${stats}*`).as("stats")
			cy.intercept("GET", `**/${list === "alerts" ? "alerts" : "case"}/status/PENDING_CUSTOMER*`).as("waiting")
			cy.visit(`/${list}`)
			cy.wait("@stats")
			const expected = seed[list].a.pending_customer
			cy.get("[data-testid=stat-pending_customer] [data-testid=stat-value]").should("have.text", String(expected))

			filterOnWaiting(list)
			cy.wait("@waiting")
			cy.get(`[data-testid=${list}-table] tbody tr`).should("have.length", expected)
			cy.get(`[data-testid=${list}-table] tbody`).should("contain", "Waiting on you")
		})
	}

	it("an item the SOC is not waiting on never offers the status", () => {
		cy.intercept("GET", "**/alerts/status/OPEN*").as("open")
		cy.visit("/alerts?status=OPEN")
		cy.wait("@open")
		cy.get("[data-testid=alerts-table] tbody tr").first().find(".n-base-selection").click()
		cy.get(".n-base-select-option:visible").should("have.length", 3).and("not.contain", "Waiting on you")
	})

	it("a waiting item shows the status, but the customer cannot pick it", () => {
		cy.intercept("GET", "**/alerts/status/PENDING_CUSTOMER*").as("waiting")
		cy.intercept("PUT", "**/alert/status").as("setStatus")
		cy.visit("/alerts?status=PENDING_CUSTOMER")
		cy.wait("@waiting")
		cy.get("[data-testid=alerts-table] tbody tr").first().find(".n-base-selection").click()
		cy.get(".n-base-select-option:visible")
			.contains("Waiting on you")
			.closest(".n-base-select-option")
			.should("have.class", "n-base-select-option--disabled")
			.click({ force: true })
		// Picking it sends nothing: the item stays as it is.
		cy.wait(500)
		cy.get("@setStatus.all").should("have.length", 0)
	})
})
