import type { PortalSeed } from "../support/e2e"

/**
 * The alerts list (#1185): one request per mount or change, no debounce on clicks, and
 * an asset filter that searches the server instead of downloading every asset name.
 * Only the latest load counts (#1192): a slower, superseded one never lands.
 */
describe("alerts list", () => {
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
		cy.intercept("GET", "**/api/incidents/db_operations/alerts?*").as("list")
		cy.visit("/alerts")

		cy.wait("@list")
		cy.get("[data-testid=alerts-table] tbody tr").should("have.length", seed.alerts.a.total)
		// Longer than the debounce that used to hide the duplicate mount request.
		cy.wait(800)
		cy.get("@list.all").should("have.length", 1)
	})

	it("reacts to a filter at once: no debounce on clicks", () => {
		let clickedAt = 0
		let requestedAt = 0
		cy.intercept("GET", "**/api/incidents/db_operations/alerts?*").as("list")
		cy.intercept("GET", "**/alerts/status/*", () => {
			requestedAt = Date.now()
		}).as("byStatus")
		cy.visit("/alerts")
		cy.wait("@list")

		cy.get("[data-testid=alerts-filter-key]").click()
		cy.get(".n-base-select-option:visible").contains(/^statuses$/).click()
		cy.get("[data-testid=alerts-filter-value]").click()
		cy.get(".n-base-select-option:visible")
			.contains(/^Open$/)
			.then($option => {
				clickedAt = Date.now()
				$option.trigger("click")
			})

		cy.wait("@byStatus").then(() => {
			// The old lists waited 400 ms before every request, clicks included.
			expect(requestedAt - clickedAt).to.be.lessThan(250)
		})
		cy.get("[data-testid=alerts-table] tbody tr").should("have.length", seed.alerts.a.open)
	})

	it("filters by asset through a server-side search", () => {
		cy.intercept("GET", "**/alerts/filter-options?*").as("options")
		cy.intercept("GET", "**/alerts/filter-options/assets*").as("assets")
		cy.intercept("GET", "**/alerts/asset/*").as("byAsset")
		cy.visit("/alerts")

		cy.wait("@options").then(({ request, response }) => {
			expect(request.url).to.include("include_assets=false")
			expect(response?.body.assets).to.have.length(0)
		})

		cy.get("[data-testid=alerts-filter-key]").click()
		cy.get(".n-base-select-option:visible").contains(/^assets$/).click()
		cy.wait("@assets")

		cy.get("[data-testid=alerts-filter-value]").click()
		cy.get("[data-testid=alerts-filter-value] input").type("a2")
		cy.wait("@assets").its("request.url").should("include", "search=a2")
		// Only the open menu: the key select's options stay in the DOM, hidden, once it closes.
		cy.get(".n-base-select-option:visible").should("have.length", 1).and("contain", "host-a2").click()

		cy.wait("@byAsset")
		cy.get("[data-testid=alerts-table] tbody tr").should("have.length", 1)
	})

	it("shows only the latest filter's rows, and stops loading, when an earlier load is slower", () => {
		const DELAY_MS = 3000
		cy.intercept("GET", "**/api/incidents/db_operations/alerts?*").as("list")
		cy.intercept("GET", "**/alerts/status/OPEN*", req => req.on("response", res => res.setDelay(DELAY_MS))).as("open")
		cy.intercept("GET", "**/alerts/status/CLOSED*").as("closed")
		cy.visit("/alerts")
		cy.wait("@list")

		cy.get("[data-testid=alerts-filter-key]").click()
		cy.get(".n-base-select-option:visible").contains(/^statuses$/).click()
		cy.get("[data-testid=alerts-filter-value]").click()
		cy.get(".n-base-select-option:visible").contains(/^Open$/).click()
		cy.get("[data-testid=alerts-table] .n-data-table-loading-wrapper").should("exist")
		// Change our mind while OPEN is still loading.
		cy.get("[data-testid=alerts-filter-value]").click()
		cy.get(".n-base-select-option:visible").contains(/^Closed$/).click()

		cy.wait("@closed")
		cy.get("[data-testid=alerts-table] tbody tr").should("have.length", seed.alerts.a.closed)
		cy.get("[data-testid=alerts-table] .n-data-table-loading-wrapper").should("not.exist")

		// Past the moment the superseded OPEN response would have arrived: still CLOSED.
		cy.wait(DELAY_MS + 500)
		cy.get("[data-testid=alerts-table] tbody tr").should("have.length", seed.alerts.a.closed)
		cy.get("[data-testid=alerts-table] .n-data-table-loading-wrapper").should("not.exist")
	})
})
