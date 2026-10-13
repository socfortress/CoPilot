import type { AlertRow, PortalSeed } from "../support/e2e"
import { alertsListRequest } from "../support/alerts"

/**
 * The alerts list's combined filters (#1245): title, status, source, asset, tags and a
 * creation-date range, all at once, all in the URL — so a link, a reload and the back
 * button give the same list. The status cards set the status filter.
 *
 * Every expectation is derived from the seed's own rows (`alert_rows`), each with its own
 * status, source, day and tags.
 */
describe("alerts: combined filters kept in the URL", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	interface Criteria {
		title?: string
		status?: string
		source?: string
		tags?: string[]
		from?: string
		to?: string
	}

	/** The seeded alert names a query must list, newest first like the list. */
	function expected(criteria: Criteria): string[] {
		return seed.alert_rows.a
			.filter(
				(row: AlertRow) =>
					(!criteria.title || row.name.toLowerCase().includes(criteria.title.toLowerCase())) &&
					(!criteria.status || row.status === criteria.status) &&
					(!criteria.source || row.source === criteria.source) &&
					(!criteria.tags || criteria.tags.some(tag => row.tags.includes(tag))) &&
					(!criteria.from || row.day >= criteria.from) &&
					(!criteria.to || row.day <= criteria.to)
			)
			.map(row => row.name)
			.reverse()
	}

	function expectRows(names: string[]) {
		if (!names.length) {
			cy.get("[data-testid=alerts-table] .n-data-table-empty").should("be.visible")
			return
		}
		cy.get("[data-testid=alerts-table] tbody tr").should("have.length", names.length)
		names.forEach((name, index) => cy.get("[data-testid=alerts-table] tbody tr").eq(index).should("contain", name))
	}

	function addFilter(label: string) {
		cy.get("[data-testid=alerts-filter-add]").click()
		cy.get(".n-dropdown-option:visible").contains(label).click()
	}

	function pick(type: string, option: string | RegExp) {
		cy.get(`[data-testid=alerts-filter-${type}] .n-base-selection`).click()
		cy.get(".n-base-select-option:visible").contains(option).click()
	}

	it("a shared link opens the list filtered by everything it names, and the controls say so", () => {
		const vip = seed.alert_tags.vip
		const days = seed.alert_rows.a.map(row => row.day).sort()
		const criteria = { title: "alert", status: "OPEN", source: "office365", tags: [vip], from: days[0], to: days.at(-1) }
		const want = expected(criteria)
		expect(want, "the link must match something").to.have.length.greaterThan(0)

		cy.intercept(alertsListRequest()).as("list")
		cy.visit(`/alerts?title=alert&status=OPEN&source=office365&tag=${vip}&from=${criteria.from}&to=${criteria.to}`)

		cy.wait("@list").then(({ request }) => {
			const params = new URL(request.url).searchParams
			expect(params.get("alert_title")).to.eq("alert")
			expect(params.get("status")).to.eq("OPEN")
			expect(params.get("source")).to.eq("office365")
			expect(params.getAll("tags")).to.deep.eq([vip])
			expect(params.get("date_from")).to.match(/Z$/)
			expect(params.get("date_to")).to.match(/Z$/)
		})
		expectRows(want)

		cy.get("[data-testid=alerts-filter-title] input").should("have.value", "alert")
		cy.get("[data-testid=alerts-filter-status]").should("contain", "Open")
		cy.get("[data-testid=alerts-filter-source]").should("contain", "office365")
		cy.get("[data-testid=alerts-filter-tag]").should("contain", vip)
		cy.get("[data-testid=alerts-filter-from] input").invoke("val").should("not.be.empty")
		cy.get("[data-testid=alerts-filter-to] input").invoke("val").should("not.be.empty")
		cy.get("[data-testid=stat-open]").should("have.attr", "aria-pressed", "true")

		// A reload gives the same list.
		cy.reload()
		expectRows(want)
		cy.get("[data-testid=alerts-filter-source]").should("contain", "office365")
	})

	it("filters built in the bar combine, and land in the URL", () => {
		const phishing = seed.alert_tags.phishing
		cy.intercept(alertsListRequest()).as("list")
		cy.visit("/alerts")
		cy.wait("@list")

		addFilter("Source")
		pick("source", /^wazuh$/)
		cy.location("search").should("contain", "source=wazuh")
		expectRows(expected({ source: "wazuh" }))

		addFilter("Tag")
		pick("tag", phishing)
		cy.get("body").type("{esc}")
		cy.location("search").should("contain", `tag=${phishing}`)
		expectRows(expected({ source: "wazuh", tags: [phishing] }))

		// Typing is debounced into one request and one URL change.
		cy.get("[data-testid=alerts-filter-title] input").type("alert 5")
		cy.location("search").should("contain", "title=alert+5")
		expectRows(expected({ source: "wazuh", tags: [phishing], title: "alert 5" }))
	})

	it("a creation-date range picked in the bar, open on one side", () => {
		const days = [...new Set(seed.alert_rows.a.map(row => row.day))].sort()
		const from = days[2]!
		const [year, month, day] = from.split("-")
		cy.intercept(alertsListRequest()).as("list")
		cy.visit("/alerts")
		cy.wait("@list")

		addFilter("Created")
		// The picker's format is the user's date format, MM/DD/YYYY by default.
		cy.get("[data-testid=alerts-filter-from] input").type(`${month}/${day}/${year}{enter}`)
		cy.get("body").click(0, 0)
		cy.location("search").should("contain", `from=${from}`).and("not.contain", "to=")
		expectRows(expected({ from }))
	})

	it("the status cards set the status, keep the other filters, and the total lets go", () => {
		cy.intercept(alertsListRequest()).as("list")
		cy.visit("/alerts?source=wazuh")
		cy.wait("@list")

		cy.get("[data-testid=stat-closed]").click()
		cy.location("search").should("contain", "status=CLOSED").and("contain", "source=wazuh")
		cy.get("[data-testid=stat-closed]").should("have.attr", "aria-pressed", "true")
		cy.get("[data-testid=alerts-filter-status]").should("contain", "Closed")
		expectRows(expected({ source: "wazuh", status: "CLOSED" }))

		cy.get("[data-testid=stat-pending_customer]").click()
		cy.location("search").should("contain", "status=PENDING_CUSTOMER")
		expectRows(expected({ source: "wazuh", status: "PENDING_CUSTOMER" }))

		cy.get("[data-testid=stat-total]").click()
		cy.location("search").should("not.contain", "status=").and("contain", "source=wazuh")
		cy.get("[data-testid=stat-total]").should("have.attr", "aria-pressed", "true")
		expectRows(expected({ source: "wazuh" }))
	})

	it("back from an alert's page returns to the same filtered list", () => {
		const url = `/alerts?status=OPEN&tag=${seed.alert_tags.phishing}`
		const want = expected({ status: "OPEN", tags: [seed.alert_tags.phishing] })
		cy.visit(url)
		expectRows(want)

		cy.get("[data-testid=alerts-table] tbody tr").first().find('button[aria-label="Open alert page"]').click()
		cy.location("pathname").should("match", /^\/alerts\/\d+$/)

		cy.go("back")
		cy.location("search").should("eq", url.slice("/alerts".length))
		expectRows(want)
		cy.get("[data-testid=alerts-filter-tag]").should("contain", seed.alert_tags.phishing)
	})

	it("criteria that match nothing say so, and one click clears them all", () => {
		cy.visit("/alerts?status=CLOSED&source=office365")
		expectRows([])

		cy.get("[data-testid=alerts-empty-clear]").click()
		cy.location("search").should("eq", "")
		expectRows(expected({}))
		cy.get("[data-testid=alerts-filter-status]").should("not.exist")
	})

	it("a link with values it cannot read shows the unfiltered list", () => {
		cy.visit("/alerts?status=ESCALATED&from=2026-02-30")
		expectRows(expected({}))
		cy.get("[data-testid=alerts-filter-status]").should("not.exist")
		cy.get("[data-testid=alerts-filter-date]").should("not.exist")
	})
})
