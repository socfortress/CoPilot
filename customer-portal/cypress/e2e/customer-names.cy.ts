import type { PortalSeed } from "../support/e2e"

/**
 * Customers by name (#1243): the token carries only codes, `GET /customer_portal/me`
 * names them and is read live.
 */
describe("customer names", () => {
	let seed: PortalSeed
	const SESSION = (s: PortalSeed) => `${s.portal_user}-names`

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
			// Two customers, granted before signing in so the token claims both.
			cy.adminApi(seed, "POST", `/auth/users/${seed.portal_user_id}/customers`, [seed.customers.a, seed.customers.b])
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed, SESSION(seed))
		// Every spec starts with the global filter empty.
		cy.window().then(win => win.localStorage.removeItem("customerFilter"))
	})

	after(() => {
		cy.adminApi(seed, "POST", `/auth/users/${seed.portal_user_id}/customers`, [seed.customers.a])
	})

	function openFilter() {
		cy.get("[data-testid=customer-filter]").click()
		return cy.get(".n-base-select-menu:visible")
	}

	it("the global filter offers customers by name, finds them by name or code, and shows the name once picked", () => {
		cy.intercept("GET", "**/api/customer_portal/me").as("me")
		cy.visit("/overview")
		cy.wait("@me").its("response.statusCode").should("eq", 200)

		openFilter().within(() => {
			cy.contains(".n-base-select-option", seed.customer_names.a).should("contain", seed.customers.a)
			cy.contains(".n-base-select-option", seed.customer_names.b).should("contain", seed.customers.b)
		})
		cy.get("[data-testid=customer-filter] input").type(seed.customers.b.toLowerCase())
		cy.get(".n-base-select-option:visible").should("have.length", 1).and("contain", seed.customer_names.b)
		cy.get("[data-testid=customer-filter] input").clear().type("rome")
		cy.get(".n-base-select-option:visible").should("have.length", 1).and("contain", seed.customer_names.a).click()
		cy.get("body").type("{esc}")

		cy.get("[data-testid=customer-filter] .n-tag").should("contain", seed.customer_names.a)
		cy.get("[data-testid=overview-scope]").should("have.text", seed.customer_names.a)
		cy.get("[data-testid=overview-scope]")
			.parent()
			.should("have.attr", "title", `Scope: ${seed.customer_names.a} (${seed.customers.a})`)
	})

	it("an alert names its customer, with the code beside it", () => {
		cy.visit(`/alerts/${seed.ai_alert_id}`)
		cy.get("[data-testid=customer-name]").should("contain", seed.customer_names.a).and("contain", seed.customers.a)
	})

	it("the profile lists every customer by name", () => {
		cy.visit("/profile")
		cy.get("[data-testid=profile-customers]").should("contain", seed.customer_names.a).and("contain", seed.customer_names.b)
	})

	it("reads the customers live: an assignment removed after login disappears without a new login", () => {
		cy.adminApi(seed, "POST", `/auth/users/${seed.portal_user_id}/customers`, [seed.customers.a])
		cy.intercept("GET", "**/api/customer_portal/me").as("me")
		cy.visit("/profile")
		cy.wait("@me")

		// The token still claims both customers; the portal shows what the server says.
		cy.get("[data-testid=profile-customers]").should("contain", seed.customer_names.a).and("not.contain", seed.customer_names.b)
		cy.get("[data-testid=customer-filter]").should("not.exist")
	})
})
