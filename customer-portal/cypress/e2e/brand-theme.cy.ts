import type { PortalSeed } from "../support/e2e"
import { colord, extend } from "colord"
import a11yPlugin from "colord/plugins/a11y"

extend([a11yPlugin])

/**
 * The portal's interface themed with the brand color (#1278), chosen in CoPilot: globally
 * for the login page and every customer, and per customer once signed in. Off, the
 * default theme stays; after a logout the customer's choice is gone with its branding.
 */
describe("brand color as the theme", () => {
	let seed: PortalSeed
	let original: Record<string, unknown>

	const BLUE = "#215ac8"
	const TEAL = "#0f766e"
	const NAVY = "#0f172a"
	const DEFAULT_LIGHT_PRIMARY = "rgb(219, 157, 0)"
	const DARK_SURFACE = "rgb(38, 40, 45)"
	const WAITING = "rgb(255, 97, 201)"

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
			cy.adminApi(seed, "GET", "/customer_portal/settings/global").then(response => {
				original = (response.body as { settings: Record<string, unknown> }).settings
			})
		})
	})

	afterEach(() => {
		cy.adminApi(seed, "DELETE", `/customer_portal/branding/${seed.customers.a}`)
	})

	after(() => {
		// Leave the global settings as the other specs expect them, whatever failed above.
		const keys = ["title", "logo_base64", "logo_mime_type", "brand_color", "theme_from_brand_color"]
		cy.adminApi(seed, "POST", "/customer_portal/settings", Object.fromEntries(keys.map(key => [key, original[key]])))
	})

	function setGlobal(fields: Record<string, unknown>) {
		cy.adminApi(seed, "PATCH", "/customer_portal/settings", fields)
	}

	function visitIn(path: string, themeName: "light" | "dark") {
		cy.visit(path, {
			onBeforeLoad(win) {
				win.localStorage.setItem("theme", JSON.stringify({ themeName }))
			}
		})
		cy.get("html").should("have.class", `theme-${themeName}`)
	}

	function readPrimary(html: JQuery<HTMLElement>) {
		return (html[0] as HTMLElement).style.getPropertyValue("--primary-color").trim()
	}

	/** Retried until the branding has loaded: the stored one shows first. */
	function expectPrimary(value: string) {
		cy.get("html").should(html => expect(readPrimary(html)).to.eq(value))
	}

	function signIn() {
		return cy.get("[data-testid=login-submit]")
	}

	it("keeps the default theme on the login page until CoPilot turns it on", () => {
		setGlobal({ brand_color: BLUE, theme_from_brand_color: false })
		visitIn("/login", "light")
		signIn().should("have.css", "background-color", DEFAULT_LIGHT_PRIMARY)
		expectPrimary(DEFAULT_LIGHT_PRIMARY)

		setGlobal({ theme_from_brand_color: true })
		visitIn("/login", "light")
		signIn().should("have.css", "background-color", "rgb(33, 90, 200)").and("have.css", "color", "rgb(255, 255, 255)")
		expectPrimary(BLUE)
	})

	it("takes the customer's own choice once signed in, and drops it at logout", () => {
		setGlobal({ brand_color: BLUE, theme_from_brand_color: false })
		cy.adminApi(seed, "PUT", `/customer_portal/branding/${seed.customers.a}`, {
			enabled: true,
			brand_color: TEAL,
			theme_from_brand_color: true
		})

		cy.loginToPortal(seed)
		visitIn("/overview", "light")
		expectPrimary(TEAL)

		cy.get("img[alt=avatar]:visible").first().click()
		cy.contains(".n-dropdown-option", "Logout").click()
		cy.location("pathname").should("eq", "/login")
		expectPrimary(DEFAULT_LIGHT_PRIMARY)
		signIn().should("have.css", "background-color", DEFAULT_LIGHT_PRIMARY)
	})

	it("keeps 'Waiting on you' in its own colour, never the brand colour", () => {
		setGlobal({ brand_color: BLUE, theme_from_brand_color: true })

		cy.loginToPortal(seed)
		visitIn("/alerts", "light")
		expectPrimary(BLUE)
		cy.get("[data-testid=stat-pending_customer] .rounded-full").should(
			"have.css",
			"background-color",
			WAITING
		)
		cy.get("[data-testid=stat-open] .rounded-full").should("not.have.css", "background-color", WAITING)
		// The list's status tag too: naive-ui has no type for it, so it takes the colour as a value.
		cy.contains("tbody tr", "Waiting on you").find(".n-tag__icon").should("have.css", "color", WAITING)
	})

	it("lets a customer turn it off while the global choice is on", () => {
		setGlobal({ brand_color: BLUE, theme_from_brand_color: true })
		cy.adminApi(seed, "PUT", `/customer_portal/branding/${seed.customers.a}`, {
			enabled: true,
			theme_from_brand_color: false
		})

		cy.loginToPortal(seed)
		visitIn("/overview", "light")
		expectPrimary(DEFAULT_LIGHT_PRIMARY)
	})

	it("lightens a dark brand color in dark mode until it stands out", () => {
		setGlobal({ brand_color: NAVY, theme_from_brand_color: true })
		visitIn("/login", "dark")
		cy.get("html").should(html => {
			const primary = readPrimary(html)
			expect(primary).to.match(/^#[0-9a-f]{6}$/)
			expect(primary).not.to.eq(NAVY)
			expect(colord(primary).contrast(DARK_SURFACE)).to.be.at.least(3)
		})
		cy.get("html").then(html => {
			signIn().should(button => {
				expect(colord(button.css("color")).contrast(readPrimary(html))).to.be.at.least(4.5)
				expect(colord(button.css("background-color")).toHex()).to.eq(readPrimary(html))
			})
		})
	})
})
