import type { PortalSeed } from "../support/e2e"
import { alertsListRequest } from "../support/alerts"

/**
 * The Activity page (#1284), on the real backend and the seed: offered only while the SOC
 * publishes it for the customer, it counts the customer's alerts and cases by when they
 * reached the SOC, and a click on a slice lists exactly the alerts it counted.
 *
 * Every seeded alert of A reached the SOC in the last week (its SLA clock), so each of the
 * three ranges holds them all and the previous period none; the expectations are derived
 * from the seed's rows.
 */
describe("activity", () => {
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
		cy.adminApi(seed, "PUT", `/customer_portal/activity/settings/${seed.customers.a}`, { enabled: true })
	})

	function countBy(values: string[]): Record<string, number> {
		return values.reduce<Record<string, number>>((counts, value) => {
			counts[value] = (counts[value] ?? 0) + 1
			return counts
		}, {})
	}

	function row(panel: string, key: string) {
		return cy.get(`[data-testid=${panel}-row][data-key="${key}"]`)
	}

	it("counts the customer's alerts and cases, slice by slice", () => {
		cy.intercept("GET", "**/api/customer_portal/activity?*").as("activity")
		cy.visit("/overview")
		// The menu renders twice (sidebar and header bar layouts): use the one on screen.
		cy.get("[data-testid=nav-activity]:visible").first().click()
		cy.location("pathname").should("eq", "/activity")
		cy.wait("@activity").its("response.statusCode").should("eq", 200)

		const rows = seed.alert_rows.a
		cy.get("[data-testid=activity-kpi-alerts] [data-testid=activity-kpi-value]").should("have.text", String(rows.length))
		cy.get("[data-testid=activity-kpi-alerts] [data-testid=activity-kpi-caption]").should(
			"have.text",
			"0 the period before"
		)
		cy.get("[data-testid=activity-kpi-cases] [data-testid=activity-kpi-value]").should(
			"have.text",
			String(seed.cases.a.total)
		)

		for (const [source, count] of Object.entries(countBy(rows.map(alert => alert.source)))) {
			row("activity-sources", source).find("[data-testid=activity-row-count]").should("have.text", String(count))
		}
		for (const [tag, count] of Object.entries(countBy(rows.flatMap(alert => alert.tags)))) {
			row("activity-tags", tag).find("[data-testid=activity-row-count]").should("have.text", String(count))
		}
		for (const [asset, count] of Object.entries(countBy(rows.flatMap(alert => alert.assets)))) {
			row("activity-assets", asset).find("[data-testid=activity-row-count]").should("have.text", String(count))
		}
		// Another customer's never counts.
		cy.get("[data-testid=activity-page]").should("not.contain", seed.customers.b)
	})

	it("lists exactly what a slice counted, with the window it counted in", () => {
		const wazuh = seed.alert_rows.a.filter(alert => alert.source === "wazuh").length
		cy.intercept(alertsListRequest()).as("list")
		cy.visit("/activity")
		row("activity-sources", "wazuh").find("[data-testid=activity-row-count]").click()

		cy.location("pathname").should("eq", "/alerts")
		cy.location("search").should("contain", "source=wazuh").and("contain", "opened_from=").and("contain", "opened_before=")
		cy.wait("@list").then(({ request }) => {
			const params = new URL(request.url).searchParams
			expect(params.get("opened_from")).to.match(/Z$/)
			expect(params.get("source")).to.eq("wazuh")
		})
		cy.get("[data-testid=alerts-filter-opened]").should("contain.text", "Reached the SOC")
		cy.get("[data-testid=alerts-table] tbody tr").should("have.length", wazuh)

		// The window is a chip like any other: removing it widens the list again.
		cy.get("[data-testid=alerts-filter-opened-remove]").click()
		cy.location("search").should("not.contain", "opened_from")
		cy.get("[data-testid=alerts-filter-source]").should("exist")
	})

	it("lists one detection exactly, not every title containing it", () => {
		const first = seed.alert_rows.a[0]!
		cy.visit("/activity")
		row("activity-detections", first.name).find("[data-testid=activity-row-label]").click()
		cy.location("search").should("contain", "detection=")
		cy.get("[data-testid=alerts-filter-detection-value]").should("have.text", first.name)
		cy.get("[data-testid=alerts-table] tbody tr").should("have.length", 1).and("contain", first.name)
	})

	it("keeps the range in the URL and counts the same week in each", () => {
		cy.intercept("GET", "**/api/customer_portal/activity?*").as("activity")
		cy.visit("/activity")
		cy.wait("@activity")
		cy.get("[data-testid=activity-range-7d]").click()
		cy.wait("@activity").then(({ request }) => {
			expect(new URL(request.url).searchParams.get("range")).to.eq("7d")
		})
		cy.location("search").should("eq", "?range=7d")
		cy.get("[data-testid=activity-kpi-alerts] [data-testid=activity-kpi-value]").should(
			"have.text",
			String(seed.alert_rows.a.length)
		)
		cy.reload()
		cy.get("[data-testid=activity-range-7d]").should("have.class", "n-radio-button--checked")
	})

	it("fits a phone's width", () => {
		cy.viewport(390, 844)
		cy.visit("/activity")
		cy.get("[data-testid=activity-sources-row]").should("have.length.greaterThan", 0)
		cy.document().then(doc => {
			expect(doc.documentElement.scrollWidth).to.be.at.most(doc.documentElement.clientWidth)
		})
	})

	it("is not offered while the SOC has not published it", () => {
		cy.adminApi(seed, "PUT", `/customer_portal/activity/settings/${seed.customers.a}`, { enabled: false })
		cy.visit("/overview")
		cy.get("[data-testid=posture-alerts]").should("exist")
		cy.get("[data-testid=nav-activity]").should("not.exist")
		cy.visit("/activity")
		cy.get("[data-testid=activity-disabled]").should("be.visible")
		cy.get("[data-testid=activity-kpi-alerts]").should("not.exist")

		cy.adminApi(seed, "PUT", `/customer_portal/activity/settings/${seed.customers.a}`, { enabled: true })
		cy.reload()
		cy.get("[data-testid=nav-activity]").should("exist")
		cy.get("[data-testid=activity-kpi-alerts]").should("exist")
	})
})
