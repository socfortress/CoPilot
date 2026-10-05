import type { PortalSeed } from "../support/e2e"

/**
 * The agents list (#1185): one page at a time from GET /customer_portal/agents, with
 * cards, filters, search and export computed on the server — never the whole fleet.
 */
describe("agents list", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
		cy.intercept("GET", "**/api/customer_portal/agents?*").as("page")
	})

	it("loads one page from the server, never the whole fleet", () => {
		cy.intercept("GET", "**/api/agents*", cy.spy().as("wholeFleet"))
		cy.visit("/agents")

		cy.wait("@page").its("request.url").should("include", "page=1").and("include", "page_size=25")
		cy.get("[data-testid=agents-table] tbody tr").should("have.length", seed.agents_a.total)
		cy.get("@page.all").should("have.length", 1)
		cy.get("@wholeFleet").should("not.have.been.called")
	})

	it("shows the cards counted on the server", () => {
		cy.visit("/agents")
		cy.wait("@page")

		const cards = {
			total: seed.agents_a.total,
			active: seed.agents_a.online,
			critical: seed.agents_a.critical,
			offline: seed.agents_a.offline
		}
		for (const [key, value] of Object.entries(cards)) {
			cy.get(`[data-testid=stat-${key}] [data-testid=stat-value]`).should("have.text", String(value))
		}
	})

	it("searches on the server once, after the user stops typing", () => {
		cy.visit("/agents")
		cy.wait("@page")

		const hostname = `ov-${seed.customers.a}-1`
		cy.get("[data-testid=agents-search] input").type(hostname)
		cy.wait("@page").its("request.url").should("include", `search=${hostname}`)
		cy.get("[data-testid=agents-table] tbody tr").should("have.length", 1).and("contain", hostname)
		// Mount + the finished word: not one request per keystroke.
		cy.get("@page.all").should("have.length", 2)
	})

	it("filters by status on the server, and the cards keep describing the whole scope", () => {
		cy.visit("/agents")
		cy.wait("@page")

		cy.get("[data-testid=agents-status]").click()
		cy.get(".n-base-select-option:visible").contains(/disconnected/i).click()
		cy.wait("@page").its("request.url").should("include", "status=disconnected")
		cy.get("[data-testid=agents-table] tbody tr").should("have.length", 1)
		cy.get("[data-testid=stat-total] [data-testid=stat-value]").should("have.text", String(seed.agents_a.total))
	})

	it("exports every filtered agent as CSV from the server", () => {
		cy.intercept("GET", "**/api/customer_portal/agents/export*").as("export")
		cy.visit("/agents")
		cy.wait("@page")

		cy.contains("button", "Export CSV").click()
		cy.wait("@export").then(({ response }) => {
			expect(response?.statusCode).to.eq(200)
			expect(response?.headers["content-type"]).to.include("text/csv")
		})
	})
})
