import type { PortalSeed } from "../support/e2e"

const TREND = "**/api/customer_portal/overview/trend*"

/**
 * The Overview's trend (#1273): alerts and cases opened and closed per day, counted by the
 * real backend from the seeded SLA clocks, with its period in the URL, a sparkline on the
 * alerts and cases cells, and a failure contained to the panel.
 */
describe("overview trend", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	function figures(opened: number, closed: number) {
		cy.get("[data-testid=overview-trend-opened]").should("have.text", String(opened))
		cy.get("[data-testid=overview-trend-closed]").should("have.text", String(closed))
		const net = opened - closed
		cy.get("[data-testid=overview-trend-net]").should("have.text", net > 0 ? `+${net}` : net < 0 ? `−${-net}` : "0")
	}

	it("counts the customer's alerts and cases opened and closed, as a separate request", () => {
		cy.intercept("GET", TREND).as("trend")
		cy.visit("/overview")
		cy.wait("@trend").then(({ request, response }) => {
			expect(new URL(request.url).searchParams.get("range")).to.eq("30d")
			expect(response?.statusCode).to.eq(200)
		})

		cy.get("[data-testid=overview-trend]").should("contain.text", "last 30 days")
		figures(seed.trend_a.alerts_opened, seed.trend_a.alerts_closed)
		cy.get("[data-testid=overview-trend-chart]").should("be.visible")
		cy.get("[data-testid=overview-trend-table] tbody tr").should("have.length", 30)

		cy.get("[data-testid=overview-trend-entity-cases]").click()
		figures(seed.trend_a.cases_opened, seed.trend_a.cases_closed)
	})

	it("draws what was opened per day on the alerts and cases cells", () => {
		cy.visit("/overview")
		cy.get("[data-testid=posture-alerts] [data-testid=posture-spark]").within(() => {
			cy.root().should("contain.text", "opened · 30d")
			cy.get("svg").should("have.attr", "aria-label", `${seed.trend_a.alerts_opened} alerts opened over the last 30 days`)
		})
		cy.get("[data-testid=posture-cases] [data-testid=posture-spark] svg")
			.invoke("attr", "aria-label")
			.should("match", new RegExp(`^${seed.trend_a.cases_opened} cases? opened`))
		cy.get("[data-testid=posture-agents] [data-testid=posture-spark]").should("not.exist")
	})

	it("keeps the period in the URL, so a reload or a shared link opens on it", () => {
		cy.intercept("GET", TREND).as("trend")
		cy.visit("/overview")
		cy.wait("@trend")

		cy.get("[data-testid=overview-trend-range-7d]").click()
		cy.wait("@trend").its("request.url").should("contain", "range=7d")
		cy.location("search").should("eq", "?trend=7d")
		cy.get("[data-testid=overview-trend]").should("contain.text", "last 7 days")
		// Every seeded clock is inside the last 7 days.
		figures(seed.trend_a.alerts_opened, seed.trend_a.alerts_closed)
		cy.get("[data-testid=overview-trend-table] tbody tr").should("have.length", 7)
		cy.get("[data-testid=posture-alerts] [data-testid=posture-spark]").should("contain.text", "opened · 7d")

		cy.reload()
		cy.wait("@trend").its("request.url").should("contain", "range=7d")
		cy.get("[data-testid=overview-trend-range-7d]").should("have.class", "n-radio-button--checked")

		cy.get("[data-testid=overview-trend-range-30d]").click()
		cy.location("search").should("eq", "")
		cy.visit("/overview?trend=90d") // unreadable: the default
		cy.wait("@trend").its("request.url").should("contain", "range=30d")
	})

	it("contains a failure to the panel, and tries again", () => {
		let failures = 1
		cy.intercept("GET", TREND, request => {
			if (failures-- > 0) request.reply({ statusCode: 500, body: { detail: "Trend unavailable" } })
		}).as("trend")
		cy.visit("/overview")
		cy.wait("@trend")

		cy.get("[data-testid=overview-trend] [data-testid=panel-error]").should("be.visible").find("button").click()
		cy.wait("@trend").its("response.statusCode").should("eq", 200)
		figures(seed.trend_a.alerts_opened, seed.trend_a.alerts_closed)
		// The rest of the Overview never noticed.
		cy.get("[data-testid=posture-alerts] [data-testid=posture-headline]").should("have.text", String(seed.alerts.a.open))
	})

	it("shows the panel on a phone without a horizontal scroll", () => {
		cy.viewport(430, 932)
		cy.visit("/overview")
		figures(seed.trend_a.alerts_opened, seed.trend_a.alerts_closed)
		cy.document().then(doc => {
			expect(doc.documentElement.scrollWidth).to.be.at.most(doc.documentElement.clientWidth)
		})
		cy.get("[data-testid=overview-trend]").screenshot("overview-trend-phone", { overwrite: true })
	})
})
