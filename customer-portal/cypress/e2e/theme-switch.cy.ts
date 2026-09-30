import type { PortalSeed } from "../support/e2e"

/**
 * The toolbar's theme switch (#1192: its view-transition animation now awaits
 * `transition.ready` instead of chaining `.then()`): each click flips the theme, with the
 * animation where the browser supports it, and nothing throws on the way.
 */
describe("theme switch", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	it("flips between the light and dark themes", () => {
		cy.visit("/overview")
		cy.get("html")
			.invoke("attr", "class")
			.then(initial => {
				const isDark = /\btheme-dark\b/.test(initial ?? "")
				const other = isDark ? "theme-light" : "theme-dark"
				const same = isDark ? "theme-dark" : "theme-light"

				cy.get("button.theme-switch").click()
				cy.get("html").should("have.class", other)
				cy.get("button.theme-switch").click()
				cy.get("html").should("have.class", same)
			})
	})
})
