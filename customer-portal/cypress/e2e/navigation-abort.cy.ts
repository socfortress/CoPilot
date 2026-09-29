import type { PortalSeed } from "../support/e2e"

/**
 * Leaving a page cancels its reads (see src/api/navigation-abort.ts). Before, Overview →
 * Alerts → Cases in quick succession left every page's calls in flight, and the page you
 * landed on waited behind them.
 *
 * The responses are delayed so the requests are still pending when we navigate; the
 * XHRs the browser actually aborted are recorded by wrapping `XMLHttpRequest`.
 */
describe("navigation cancels the previous page's requests", () => {
	let seed: PortalSeed
	const DELAY_MS = 5000

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	function recordAborts(win: Cypress.AUTWindow) {
		const aborted: string[] = []
		const opened = new WeakMap<XMLHttpRequest, string>()
		const { open, abort } = win.XMLHttpRequest.prototype
		win.XMLHttpRequest.prototype.open = function (this: XMLHttpRequest, method: string, url: string | URL, ...rest: unknown[]) {
			opened.set(this, `${method.toUpperCase()} ${String(url)}`)
			return (open as (...args: unknown[]) => void).call(this, method, url, ...rest)
		}
		win.XMLHttpRequest.prototype.abort = function (this: XMLHttpRequest) {
			aborted.push(opened.get(this) ?? "?")
			return abort.call(this)
		}
		Object.assign(win, { __aborted: aborted })
	}

	const aborted = () => cy.window().its("__aborted") as Cypress.Chainable<string[]>

	const delayed = (req: { on: (event: "response", handler: (res: { setDelay: (ms: number) => void }) => void) => void }) =>
		req.on("response", res => res.setDelay(DELAY_MS))

	it("Overview → Alerts → Cases: only the last page's reads stay alive", () => {
		cy.intercept("GET", "**/api/customer_portal/overview*", delayed).as("overview")
		cy.intercept("GET", "**/api/customer_portal/dashboard/alert-stats*", delayed).as("alertStats")
		cy.intercept("GET", "**/api/incidents/db_operations/alerts?*", delayed).as("alerts")
		cy.intercept("GET", "**/api/incidents/db_operations/cases?*").as("cases")

		cy.visit("/overview", { onBeforeLoad: recordAborts })
		cy.get("@overview.all").should("have.length", 1)

		cy.get('a[href="/alerts"]').first().click()
		cy.location("pathname").should("eq", "/alerts")
		cy.get("@alerts.all").should("have.length", 1)
		aborted().should(list => {
			expect(list.some(entry => entry.startsWith("GET") && entry.includes("/customer_portal/overview"))).to.eq(true)
		})

		cy.get('a[href="/cases"]').first().click()
		cy.location("pathname").should("eq", "/cases")
		aborted().should(list => {
			expect(list.some(entry => entry.includes("/incidents/db_operations/alerts?"))).to.eq(true)
			expect(list.some(entry => entry.includes("/customer_portal/dashboard/alert-stats"))).to.eq(true)
		})

		// The page we landed on loads normally, well before the abandoned calls would have
		// answered, and none of its own requests was cancelled.
		cy.wait("@cases")
		cy.get("[data-testid=cases-table] tbody tr", { timeout: DELAY_MS - 1000 }).should(
			"have.length",
			seed.cases.a.total
		)
		aborted().should(list => {
			expect(list.filter(entry => entry.includes("/incidents/db_operations/cases"))).to.have.length(0)
			expect(list.filter(entry => entry.includes("/customer_portal/settings")), "branding survives").to.have.length(0)
		})
	})

	it("a query-string change on the same page cancels nothing", () => {
		cy.intercept("GET", "**/api/incidents/db_operations/cases?*", delayed).as("cases")
		cy.visit("/cases", { onBeforeLoad: recordAborts })
		cy.get("@cases.all").should("have.length", 1)
		cy.window().then(win => {
			// The app's own router, reached through the mounted app instance.
			const app = (win.document.querySelector("#app") as unknown as { __vue_app__: any }).__vue_app__
			return app.config.globalProperties.$router.replace({ query: { e2e: "1" } })
		})
		cy.location("search").should("contain", "e2e=1")
		// The list's request, in flight during the query change, still answers.
		cy.wait("@cases", { timeout: DELAY_MS + 5000 })
		cy.get("[data-testid=cases-table] tbody tr").should("have.length", seed.cases.a.total)
		aborted().should("have.length", 0)
	})
})
