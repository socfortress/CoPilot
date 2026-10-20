import type { PortalSeed } from "../support/e2e"
import { event, EVENT_TOTAL, eventSources, FIELDS, PAGE, resetEventSearchMemory } from "../support/event-search"

/**
 * Event search's saved and recent queries, CSV export and column picker (#1258). The page,
 * the login and the user's memory (kept on the backend, so it follows them to any device)
 * are real; the indexer's answers (sources, fields, events) are served at the network
 * layer, since the e2e backend runs without one.
 */
describe("event search: saved queries, CSV export and columns", () => {
	let seed: PortalSeed
	const NOW = Date.UTC(2026, 9, 15, 9, 0, 0)

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
		const customer = seed.customers.a
		// The memory lives on the server: each test starts from one that holds nothing.
		resetEventSearchMemory(seed, customer)
		cy.intercept({ method: "GET", pathname: `/api/siem/event_search/${customer}` }).as("memory")
		cy.intercept({ method: "GET", pathname: `/api/siem/event_sources/${customer}` }, {
			success: true,
			message: "ok",
			event_sources: eventSources(customer)
		}).as("sources")
		cy.intercept({ method: "GET", url: new RegExp(`/api/siem/events/${customer}/[^/?]+/fields`) }, {
			success: true,
			message: "ok",
			fields: FIELDS,
			total: FIELDS.length,
			index_pattern: "*"
		}).as("fields")
		cy.intercept({ method: "GET", url: new RegExp(`/api/siem/events/${customer}/[^/?]+\\?`) }, req => {
			const url = new URL(req.url)
			const more = url.searchParams.get("scroll_id")
			const events = more
				? Array.from({ length: EVENT_TOTAL - PAGE }, (_, i) => event(PAGE + i))
				: Array.from({ length: PAGE }, (_, i) => event(i))
			req.reply({
				success: true,
				message: "ok",
				events,
				total: EVENT_TOTAL,
				scroll_id: more ? null : "scroll-1",
				page_size: PAGE
			})
		}).as("events")
	})

	function visit() {
		cy.visit("/event-search")
		cy.wait(["@sources", "@memory"])
	}

	function pickSource(name: string) {
		cy.get("[data-testid=event-search-source]").click()
		cy.get(".n-base-select-option:visible").contains(name).click()
		cy.wait("@fields")
	}

	function search(query: string) {
		cy.get("[data-testid=event-search-query] textarea").clear().type(query, { delay: 0 })
		cy.get("[data-testid=event-search-submit]").click()
		return cy.wait("@events")
	}

	/**
	 * The table's headers, retried until they match: a `.then()` would read them once, at
	 * whatever render the click landed on, and fail when the table had not caught up yet.
	 */
	function expectHeaders(expected: string[]) {
		cy.get("[data-testid=event-results] thead th").should($th => {
			expect([...$th].map(th => th.textContent?.trim()).filter(Boolean)).to.deep.equal(expected)
		})
	}

	it("saves a search under a name, finds it on another device, and runs it again from the list", () => {
		visit()
		pickSource("Wazuh Alerts")
		search("rule_level:>=10")

		cy.get("[data-testid=save-query-toggle]").click()
		cy.get("[data-testid=save-query-name] input").type("High level alerts")
		cy.get("[data-testid=save-query-submit]").click()
		cy.contains("Saved “High level alerts”")

		// Another device: a browser with nothing stored, signed in afresh.
		cy.clearAllLocalStorage()
		cy.clearAllSessionStorage()
		cy.loginToPortal(seed, "event-search-other-device")
		visit()
		cy.get("[data-testid=saved-queries-toggle]").should("contain", "1").click()
		cy.get("[data-testid=saved-query]")
			.should("have.length", 1)
			.and("contain", "High level alerts")
			.and("contain", "rule_level:>=10")
			.and("contain", "Wazuh Alerts · last 24 hours")
			.find("button")
			.first()
			.click()

		cy.wait("@events").then(({ request }) => {
			const url = new URL(request.url)
			expect(url.pathname).to.contain("/Wazuh%20Alerts")
			expect(url.searchParams.get("query")).to.eq("rule_level:>=10")
			expect(url.searchParams.get("timerange")).to.eq("24h")
		})
		cy.get("[data-testid=event-search-query] textarea").should("have.value", "rule_level:>=10")
	})

	it("lists the searches run, newest first and once each; a saved one is updated by its name, and deleted", () => {
		visit()
		pickSource("Wazuh Alerts")
		search("first")
		search("second")
		search("first")

		cy.get("[data-testid=saved-queries-toggle]").click()
		cy.get("[data-testid=recent-query]").should("have.length", 2)
		cy.get("[data-testid=recent-query]").first().should("contain", "first")
		cy.get("[data-testid=recent-queries-clear]").click()
		cy.get("[data-testid=recent-query]").should("not.exist")
		cy.get("body").type("{esc}")

		for (const query of ["one", "two"]) {
			search(query)
			cy.get("[data-testid=save-query-toggle]").click()
			cy.get("[data-testid=save-query-name] input").type("Mine")
			cy.get("[data-testid=save-query-submit]").click()
		}
		cy.contains("Updated “Mine”")
		cy.get("[data-testid=saved-queries-toggle]").click()
		cy.get("[data-testid=saved-query]").should("have.length", 1).and("contain", "two")
		cy.get("[data-testid=saved-query-delete]").click()
		cy.get("[data-testid=saved-query]").should("not.exist")
	})

	it("exports the loaded events in the columns on screen, with ISO times, and says when more remain", () => {
		cy.clock(NOW, ["Date"])
		visit()
		pickSource("Wazuh Alerts")
		search("*")

		cy.get("[data-testid=event-results-count]").should("contain", `${PAGE} of ${EVENT_TOTAL} events loaded`)
		cy.get("[data-testid=event-export]").click()
		cy.contains(`Exported ${PAGE} of ${EVENT_TOTAL} events: load more to include the rest`)
		const file = "cypress/downloads/events-Wazuh_Alerts-2026-10-15-09-00-00.csv"
		cy.readFile(file).then((text: string) => {
			const lines = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/)
			expect(lines[0]).to.eq("Timestamp,Level,Source,Rule")
			expect(lines[1]).to.eq("2026-10-01T12:00:00.000Z,3,web-00,Login session opened")
			expect(lines).to.have.length(PAGE + 1)
		})

		cy.contains("Load More").click()
		cy.wait("@events")
		cy.get("[data-testid=event-export]").click()
		cy.contains(`Exported ${EVENT_TOTAL} events`)
		cy.readFile(file).then((text: string) => {
			expect(text.trim().split(/\r?\n/)).to.have.length(EVENT_TOTAL + 1)
		})
	})

	it("picks a source's columns, keeps them across a reload, exports them, and goes back to the SOC's layout", () => {
		cy.clock(NOW, ["Date"])
		visit()
		pickSource("Office 365")
		search("*")
		expectHeaders(["Time", "User", "Actions"])

		cy.get("[data-testid=event-columns-toggle]").click()
		cy.get("[data-testid=picked-column]").should("have.length", 2)
		cy.get("[data-testid=column-picker-add]").click()
		cy.get(".n-base-select-option:visible").contains("data_srcip").click()
		cy.get("[data-testid=picked-column-label] input").last().clear().type("Source IP")
		// Move the new column to the front: two steps up.
		cy.get("[data-testid=picked-column]").last().find("button[aria-label='Move left']").click()
		cy.get("[data-testid=picked-column]").eq(1).find("button[aria-label='Move left']").click()
		cy.get("[data-testid=column-picker-save]").click()
		expectHeaders(["Source IP", "Time", "User", "Actions"])

		cy.get("[data-testid=event-export]").click()
		cy.readFile("cypress/downloads/events-Office_365-2026-10-15-09-00-00.csv").should(
			"contain",
			"Source IP,Time,User\r\n203.0.113.0,2026-10-01T12:00:00.000Z,user0@acme.test"
		)

		cy.reload()
		cy.wait(["@sources", "@memory"])
		pickSource("Office 365")
		search("*")
		expectHeaders(["Source IP", "Time", "User", "Actions"])

		// The choice is per source: another source keeps its own layout.
		pickSource("Wazuh Alerts")
		search("*")
		expectHeaders(["Timestamp", "Level", "Source", "Rule", "Actions"])

		pickSource("Office 365")
		search("*")
		cy.get("[data-testid=event-columns-toggle]").click()
		cy.get("[data-testid=column-picker-reset]").click()
		expectHeaders(["Time", "User", "Actions"])
	})

	it("saves column templates, previews and switches between them, and finds them on another device", () => {
		visit()
		pickSource("Office 365")
		search("*")
		cy.get("[data-testid=column-layouts-current]").should("have.text", "SOC layout")

		// A template from the columns being edited: the SOC's two, plus the source address.
		cy.get("[data-testid=event-columns-toggle]").click()
		cy.get("[data-testid=column-picker-add]").click()
		cy.get(".n-base-select-option:visible").contains("data_srcip").click()
		cy.get("[data-testid=picked-column-label] input").last().clear().type("Source IP")
		cy.get("[data-testid=column-template-name] input").type("Network")
		cy.get("[data-testid=column-template-save]").click()
		cy.contains("Saved the template “Network”")
		cy.get("[data-testid=column-template]").should("have.length", 1).and("contain", "Time · User · Source IP")
		cy.get("[data-testid=column-template-name] input").should("have.value", "")
		// Saving a template applies nothing.
		cy.get("[data-testid=column-picker]").parents(".n-card").find("[aria-label=close]").first().click()
		expectHeaders(["Time", "User", "Actions"])

		// Each layout is previewed before it is picked: every column, its header and field.
		cy.get("[data-testid=column-layouts-toggle]").click()
		cy.get("[data-testid=column-layout]").should("have.length", 2)
		cy.get("[data-testid=columns-preview-column]").should("have.length", 2)
		cy.get("[data-testid=column-layout]").eq(1).trigger("mouseenter")
		cy.get("[data-testid=columns-preview-column]").then($rows => {
			expect([...$rows].map(row => [...row.querySelectorAll("span")].map(cell => cell.textContent?.trim()))).to.deep.equal([
				["1", "Time", "timestamp"],
				["2", "User", "data_office365_UserId"],
				["3", "Source IP", "data_srcip"]
			])
		})
		cy.get("[data-testid=column-layout]").eq(1).click()
		expectHeaders(["Time", "User", "Source IP", "Actions"])
		cy.get("[data-testid=column-layouts-current]").should("have.text", "Network")

		// Another device finds the template and the layout in force.
		cy.clearAllLocalStorage()
		cy.clearAllSessionStorage()
		cy.loginToPortal(seed, "event-search-templates-device")
		visit()
		pickSource("Office 365")
		search("*")
		expectHeaders(["Time", "User", "Source IP", "Actions"])
		cy.get("[data-testid=column-layouts-current]").should("have.text", "Network")
		cy.get("[data-testid=column-layouts-toggle]").click()
		cy.get("[data-testid=column-layout]").first().click()
		expectHeaders(["Time", "User", "Actions"])

		// Deleting asks first, in the Layout menu…
		cy.get("[data-testid=column-layouts-toggle]").click()
		cy.get("[data-testid=column-layout-delete]").click()
		cy.get("[data-testid=template-delete-confirm]").should("contain", "Delete “Network”?")
		cy.get("[data-testid=template-delete-cancel]").click()
		cy.get("[data-testid=column-layout]").should("have.length", 2)
		cy.get("[data-testid=column-layout-delete]").click()
		cy.get("[data-testid=template-delete-confirm-button]").click()
		cy.contains("Deleted the template “Network”")
		cy.get("[data-testid=column-layout]").should("have.length", 1)
		cy.get("[data-testid=column-layouts-toggle]").click()

		// …and in the Columns dialog.
		cy.get("[data-testid=event-columns-toggle]").click()
		cy.get("[data-testid=column-template-name] input").type("Quick")
		cy.get("[data-testid=column-template-save]").click()
		cy.get("[data-testid=column-template]").should("have.length", 1)
		cy.get("[data-testid=column-template-delete]").click()
		cy.get("[data-testid=template-delete-confirm]").should("contain", "Delete “Quick”?")
		cy.get("[data-testid=template-delete-cancel]").click()
		cy.get("[data-testid=column-template]").should("have.length", 1).and("contain", "Quick")
		cy.get("[data-testid=column-template-delete]").click()
		cy.get("[data-testid=template-delete-confirm-button]").click()
		cy.get("[data-testid=column-template]").should("not.exist")
	})

	it("a saved search whose source is gone says so instead of running", () => {
		visit()
		pickSource("Office 365")
		search("x")
		cy.get("[data-testid=save-query-toggle]").click()
		cy.get("[data-testid=save-query-name] input").type("Office")
		cy.get("[data-testid=save-query-submit]").click()

		cy.contains("Saved “Office”")
		// The SOC removes the source.
		cy.intercept({ method: "GET", pathname: `/api/siem/event_sources/${seed.customers.a}` }, {
			success: true,
			message: "ok",
			event_sources: eventSources(seed.customers.a).filter(s => s.name !== "Office 365")
		})
		cy.reload()
		cy.wait("@memory")
		cy.get("[data-testid=saved-queries-toggle]").click()
		cy.get("[data-testid=saved-query] button").first().click()
		cy.contains("The source “Office 365” is no longer available for this customer")
	})
})
