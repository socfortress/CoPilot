import type { PortalSeed } from "../support/e2e"

/** The cases list (#1185): one request on mount, and a filter reacts without a debounce. */
describe("cases list", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	it("loads with a single request", () => {
		cy.intercept("GET", "**/api/incidents/db_operations/cases?*").as("list")
		cy.visit("/cases")

		cy.wait("@list")
		cy.get("[data-testid=cases-table] tbody tr").should("have.length", seed.cases.a.total)
		// Longer than the debounce that used to hide the duplicate mount request.
		cy.wait(800)
		cy.get("@list.all").should("have.length", 1)
	})

	it("reacts to a filter at once: no debounce on clicks", () => {
		let clickedAt = 0
		let requestedAt = 0
		cy.intercept("GET", "**/api/incidents/db_operations/cases?*").as("list")
		cy.intercept("GET", "**/case/status/*", () => {
			requestedAt = Date.now()
		}).as("byStatus")
		cy.visit("/cases")
		cy.wait("@list")

		cy.get("[data-testid=cases-filter-key]").click()
		cy.get(".n-base-select-option:visible").contains(/^statuses$/).click()
		cy.get("[data-testid=cases-filter-value]").click()
		cy.get(".n-base-select-option:visible")
			.contains(/^Open$/)
			.then($option => {
				clickedAt = Date.now()
				$option.trigger("click")
			})

		cy.wait("@byStatus").then(() => {
			expect(requestedAt - clickedAt).to.be.lessThan(250)
		})
		cy.get("[data-testid=cases-table] tbody tr").should("have.length", seed.cases.a.open)
	})
})
