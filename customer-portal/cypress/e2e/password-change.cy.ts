import type { PortalSeed } from "../support/e2e"

/**
 * A password an admin chose must be replaced (#1277). On the real backend: an account the
 * SOC creates signs in to the change page and nothing else, keeps where it was going, can
 * only sign out otherwise, and continues once the password is its own. An admin reset holds
 * a signed-in user again at their next request.
 */
describe("password change after an admin-set password", () => {
	let seed: PortalSeed
	const username = `e2e_pwc_${Date.now()}`
	const given = "Given-By-Admin-2026!"
	const chosen = "My-Own-Choice-2026!"
	const reset = "Reset-By-Admin-2026!"

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
			cy.adminApi(seed, "POST", "/auth/register", {
				username,
				password: given,
				email: `${username}@e2e.example`,
				role_id: 4,
				customer_codes: [seed.customers.a]
			})
		})
	})

	after(() => {
		// The account is the spec's own: leave the seed as the other specs expect it.
		cy.adminApi(seed, "GET", `/auth/security/customers/${seed.customers.a}/users`).then(response => {
			const user = (response.body.users as { id: number; username: string }[]).find(u => u.username === username)
			if (user) cy.adminApi(seed, "DELETE", `/auth/delete/${user.id}`)
		})
	})

	function signIn(password: string) {
		cy.visit("/login")
		cy.get("[data-testid=login-username] input").type(username)
		cy.get("[data-testid=login-password] input").type(password, { log: false })
		cy.get("[data-testid=login-submit]").click()
	}

	function choose(current: string, next: string, confirm = next) {
		cy.get("[data-testid=change-password-current] input").clear().type(current, { log: false })
		cy.get("[data-testid=change-password-new] input").clear().type(next, { log: false })
		cy.get("[data-testid=change-password-confirm] input").clear().type(confirm, { log: false })
		cy.get("[data-testid=change-password-submit]").click()
	}

	it("signs in to the change and nothing else, until the password is the user's own", () => {
		cy.intercept("GET", "**/api/customer_portal/overview*").as("overview")
		signIn(given)
		cy.location("pathname").should("eq", "/change-password")
		cy.get("[data-testid=change-password-page]")
			.should("contain.text", "Choose a new password")
			.and("contain.text", username)
			.and("contain.text", "Password you received")

		// Any page leads back here, remembering where the user was going; none of them loads.
		cy.visit("/alerts?status=OPEN")
		cy.location("pathname").should("eq", "/change-password")
		cy.location("search").should(search => {
			expect(new URLSearchParams(search).get("redirect")).to.eq("/alerts?status=OPEN")
		})
		cy.get("@overview.all").should("have.length", 0)

		// The API holds the user too, with the header the portal reads, never a 401.
		cy.request({ method: "POST", url: "/api/auth/token/customer-portal", form: true, body: { username, password: given } })
			.its("body.access_token")
			.then(token =>
				cy.request({
					url: "/api/customer_portal/overview",
					headers: { Authorization: `Bearer ${token}` },
					failOnStatusCode: false
				})
			)
			.then(response => {
				expect(response.status).to.eq(403)
				expect(response.headers["x-password-change-required"]).to.eq("true")
			})

		// Refusals keep the user here.
		choose("Wrong-Guess-2026!", chosen)
		cy.contains("Current password is incorrect").should("be.visible")
		choose(given, given)
		cy.contains("Choose a password different from the current one").should("be.visible")
		cy.location("pathname").should("eq", "/change-password")

		choose(given, chosen)
		cy.location("pathname").should("eq", "/alerts")
		cy.location("search").should("eq", "?status=OPEN")

		// Released for good: a reload and the Overview open normally.
		cy.reload()
		cy.location("pathname").should("eq", "/alerts")
		cy.visit("/overview")
		cy.wait("@overview").its("response.statusCode").should("eq", 200)
		cy.location("pathname").should("eq", "/overview")
	})

	it("can only sign out otherwise", () => {
		cy.adminApi(seed, "POST", "/auth/reset-password", { username, new_password: given })
		signIn(given)
		cy.location("pathname").should("eq", "/change-password")
		cy.get("[data-testid=change-password-cancel]").should("have.text", "Sign out").click()
		cy.location("pathname").should("eq", "/login")
		cy.visit("/overview")
		cy.location("pathname").should("eq", "/login")
	})

	it("holds a signed-in user again at their next request after an admin reset", () => {
		signIn(given)
		choose(given, chosen)
		cy.location("pathname").should("eq", "/overview")

		cy.adminApi(seed, "POST", "/auth/reset-password", { username, new_password: reset })
		// The next page's request is refused: the portal goes to the change instead of failing.
		cy.get("a[href='/alerts']:visible").first().click()
		cy.location("pathname").should("eq", "/change-password")
		cy.location("search").should("contain", "redirect=")

		choose(reset, "Another-Own-2026!")
		cy.location("pathname").should("eq", "/alerts")
	})
})
