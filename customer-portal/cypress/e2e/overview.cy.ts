import type { PortalSeed } from "../support/e2e"

/**
 * The portal Overview (#1181): one request for the whole page, showing exactly the
 * seeded rows, with a failing section contained to that section.
 */
describe("overview", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	it("loads with a single request instead of the four it replaced", () => {
		const replaced = [
			"**/api/incidents/db_operations/alerts?*",
			"**/api/incidents/db_operations/cases?*",
			"**/api/agents*",
			"**/api/customer_portal/ai_reports/insights*"
		]
		replaced.forEach((url, index) => cy.intercept("GET", url, cy.spy().as(`replaced${index}`)))
		cy.intercept("GET", "**/api/customer_portal/overview*").as("overview")

		cy.visit("/overview")
		cy.wait("@overview").its("response.statusCode").should("eq", 200)
		cy.get("[data-testid=recent-alerts] [data-testid=activity-item]").should("have.length", 6)

		cy.get("@overview.all").should("have.length", 1)
		replaced.forEach((_, index) => cy.get(`@replaced${index}`).should("not.have.been.called"))
	})

	it("shows the seeded posture: open items, totals, agents", () => {
		cy.visit("/overview")

		cy.get("[data-testid=posture-alerts]").within(() => {
			cy.get("[data-testid=posture-headline]").should("have.text", String(seed.alerts.a.open))
			cy.get("[data-testid=posture-footnote]").should("have.text", `${seed.alerts.a.total} total`)
		})
		cy.get("[data-testid=posture-cases]").within(() => {
			cy.get("[data-testid=posture-headline]").should("have.text", String(seed.cases.a.open))
			cy.get("[data-testid=posture-footnote]").should("have.text", `${seed.cases.a.total} total`)
		})
		cy.get("[data-testid=posture-agents]").within(() => {
			cy.get("[data-testid=posture-headline]").should(
				"have.text",
				`${seed.agents_a.online}/${seed.agents_a.total}`
			)
			cy.get("[data-testid=posture-footnote]").should("have.text", `${seed.agents_a.critical} critical`)
		})
	})

	it("lists the recent alerts and cases of the user's customer only", () => {
		cy.visit("/overview")

		cy.get("[data-testid=recent-alerts] [data-testid=activity-item]")
			.should("have.length", seed.alerts.a.total)
			.first()
			.should("contain", `${seed.customers.a} alert 5`)
		// Assets travel with the light projection: "first +N" on the alert that has two.
		cy.get("[data-testid=recent-alerts]").should("contain", "host-a1 +1").and("not.contain", seed.customers.b)

		cy.get("[data-testid=recent-cases] [data-testid=activity-item]").should("have.length", seed.cases.a.total)
		cy.get("[data-testid=recent-cases]")
			.should("contain", "2 alerts")
			.and("contain", "analyst1")
			.and("contain", "unassigned")
			.and("not.contain", seed.customers.b)
	})

	it("shows the latest AI finding per alert", () => {
		cy.visit("/overview")

		// Alert 0 has an older Low report and a newer High one: only High may show.
		cy.get("[data-testid=ai-findings]")
			.should("contain", "High finding")
			.and("contain", "Medium finding")
			.and("not.contain", "Low finding")
	})

	it("keeps the other sections when one fails", () => {
		cy.intercept("GET", "**/api/customer_portal/overview*", request => {
			request.continue(response => {
				response.body.cases.error = "Failed to load cases"
			})
		})

		cy.visit("/overview")

		cy.get("[data-testid=recent-cases] [data-testid=panel-error]").should("contain", "Failed to load cases")
		cy.get("[data-testid=posture-cases] [data-testid=posture-error]").should("contain", "Failed to load cases")
		cy.get("[data-testid=recent-alerts] [data-testid=activity-item]").should("have.length", seed.alerts.a.total)
		cy.get("[data-testid=posture-alerts] [data-testid=posture-headline]").should(
			"have.text",
			String(seed.alerts.a.open)
		)
		cy.get("[data-testid=ai-findings]").should("exist")
	})
})
