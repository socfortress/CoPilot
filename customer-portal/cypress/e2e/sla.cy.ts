import type { PortalSeed } from "../support/e2e"

/**
 * The SLA page and the "waiting on you" status (#1187): the page is offered only while
 * the SOC publishes it for the customer, shows the seeded figures of the user's customer,
 * and links to what waits on the customer; replying to a waiting item hands it back.
 */
describe("service levels", () => {
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
		cy.adminApi(seed, "PUT", `/customer_portal/sla/settings/${seed.customers.a}`, { enabled: true })
	})

	function kpi(key: string) {
		return cy.get(`[data-testid=sla-kpi-${key}]`)
	}

	it("shows the customer's figures: compliance, response times, what is open and the promise", () => {
		cy.intercept("GET", "**/api/customer_portal/sla/overview*").as("overview")
		cy.visit("/overview")
		// The menu renders twice (sidebar and header bar layouts): use the one on screen.
		cy.get("[data-testid=nav-sla]:visible").first().click()
		cy.location("pathname").should("eq", "/sla")
		cy.wait("@overview").its("response.statusCode").should("eq", 200)

		kpi("alert-acknowledge").within(() => {
			cy.get("[data-testid=sla-kpi-rate]").should("contain.text", `${seed.sla_a.ack_rate}%`)
			cy.get("[data-testid=sla-kpi-count]").should(
				"have.text",
				`${seed.sla_a.ack_met} of ${seed.sla_a.alerts_opened} on target`
			)
			cy.get("[data-testid=sla-kpi-median]").invoke("text").should("match", /\d+m/)
		})
		kpi("alert-resolve").find("[data-testid=sla-kpi-rate]").should("contain.text", "100%")

		cy.get("[data-testid=sla-open-alerts] [data-testid=sla-open-value]").should(
			"contain.text",
			String(seed.sla_a.open_alerts)
		)
		cy.get("[data-testid=sla-open-cases] [data-testid=sla-open-value]").should(
			"contain.text",
			String(seed.sla_a.open_cases)
		)
		cy.get("[data-testid=sla-open-waiting] [data-testid=sla-open-value]").should(
			"contain.text",
			String(seed.sla_a.waiting_on_you)
		)

		cy.get("[data-testid=sla-target-alert-critical]").should("contain", "15 min").and("contain", "4 h")
		cy.get("[data-testid=sla-target-alert-high]").should("contain", "1 h").and("contain", "8 h")
		cy.get("[data-testid=sla-target-alert-informational]").should("not.exist") // no promise, not listed
		cy.get("[data-testid=sla-page]").should("not.contain", "analyst1") // never who did the work
	})

	it("reloads for another period, scoped the same way", () => {
		cy.intercept("GET", "**/api/customer_portal/sla/overview*").as("overview")
		cy.visit("/sla")
		cy.wait("@overview")
		cy.get("[data-testid=sla-period-7d]").click()
		cy.wait("@overview").then(({ request }) => {
			const from = new Date(new URL(request.url).searchParams.get("date_from") ?? "")
			const days = (Date.now() - from.getTime()) / 86_400_000
			expect(days).to.be.closeTo(7, 0.1)
		})
		kpi("alert-acknowledge").find("[data-testid=sla-kpi-rate]").should("contain.text", `${seed.sla_a.ack_rate}%`)
	})

	it("links what waits on the customer to the filtered alerts list", () => {
		cy.intercept("GET", "**/alerts/status/PENDING_CUSTOMER*").as("waiting")
		cy.visit("/sla")
		cy.get("[data-testid=sla-open-waiting-alerts]").click()
		cy.location("search").should("contain", "status=PENDING_CUSTOMER")
		cy.wait("@waiting")
		cy.get("[data-testid=alerts-table] tbody tr").should("have.length", seed.alerts.a.pending_customer)
	})

	it("links the open alerts and cases to their lists, unfiltered: open is every status but closed", () => {
		cy.visit("/sla")
		cy.get("[data-testid=sla-open-alerts-view-all]").should("contain.text", "View all").click()
		cy.location("pathname").should("eq", "/alerts")
		cy.location("search").should("not.contain", "status=")
		cy.get("[data-testid=alerts-table]").should("be.visible")

		cy.visit("/sla")
		cy.get("[data-testid=sla-open-cases-view-all]").click()
		cy.location("pathname").should("eq", "/cases")
		cy.location("search").should("not.contain", "status=")
		cy.get("[data-testid=cases-table]").should("be.visible")
	})

	it("is not offered while the SOC has not published it", () => {
		cy.adminApi(seed, "PUT", `/customer_portal/sla/settings/${seed.customers.a}`, { enabled: false })
		cy.visit("/overview")
		cy.get("[data-testid=posture-alerts]").should("exist")
		cy.get("[data-testid=nav-sla]").should("not.exist")
		cy.visit("/sla")
		cy.get("[data-testid=sla-disabled]").should("be.visible")
		cy.get("[data-testid=sla-kpi-alert-acknowledge]").should("not.exist")

		cy.adminApi(seed, "PUT", `/customer_portal/sla/settings/${seed.customers.a}`, { enabled: true })
		cy.reload()
		cy.get("[data-testid=nav-sla]").should("exist")
		cy.get("[data-testid=sla-kpi-alert-acknowledge]").should("exist")
	})

	it("a waiting alert says so, and replying hands it back to the SOC", () => {
		cy.intercept("POST", "**/alert/comment").as("comment")
		cy.visit(`/alerts/${seed.waiting_alert_id}`)
		cy.get("[data-testid=waiting-on-you]").should("be.visible")
		cy.get("[data-testid=waiting-on-you-reply]").click()
		cy.get("[data-testid=comment-input] textarea").should("be.visible").type("Yes, that login was ours.")
		cy.get("[data-testid=comment-submit]").click()
		cy.wait("@comment").its("response.statusCode").should("eq", 200)
		cy.get("[data-testid=waiting-on-you]").should("not.exist")
	})

	it("a waiting case says so too", () => {
		cy.visit(`/cases/${seed.waiting_case_id}`)
		cy.get("[data-testid=waiting-on-you]").should("be.visible").and("contain", "case")
	})
})
