import type { PortalSeed } from "../support/e2e"

/** What the SMTP sink in cypress.config.ts received. */
interface SinkMessage {
	to: string[]
	subject: string
	data: string
}

/**
 * A customer admin manages their customers' portal users (#1296), against the real backend: the
 * SOC appoints the seeded portal user as an admin of customer A, who finds Users in the avatar
 * menu, invites a colleague (the temporary password goes to the SMTP sink Cypress runs), and
 * disables one whose session is open: it ends at its next request on a sign-in page that says
 * why, and their sign-in is refused until they are enabled again.
 */
describe("users", () => {
	let seed: PortalSeed
	const run = Date.now().toString(36)
	const colleague = { username: `e2e_cy_col_${run}`, password: "Colleague-Own-2026!" }
	const invited = `e2e_cy_inv_${run}`
	const created: string[] = []

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
			cy.adminApi(
				seed,
				"PUT",
				`/auth/security/customers/${seed.customers.a}/users/${seed.portal_user_id}/customer-admin`,
				{
					is_customer_admin: true
				}
			)
			// A colleague of customer A, signed in with a password of their own (not held on the change).
			cy.adminApi(seed, "POST", "/auth/register", {
				username: colleague.username,
				password: seed.password,
				email: `${colleague.username}@e2e.example`,
				role_id: 4,
				customer_codes: [seed.customers.a]
			})
			created.push(colleague.username)
			cy.request({
				method: "POST",
				url: "/api/auth/token/customer-portal",
				form: true,
				body: { username: colleague.username, password: seed.password }
			}).then(({ body }) =>
				cy.request({
					method: "POST",
					url: "/api/auth/reset-password/me",
					body: {
						username: colleague.username,
						current_password: seed.password,
						new_password: colleague.password
					},
					headers: { Authorization: `Bearer ${body.access_token}` }
				})
			)
		})
	})

	beforeEach(() => {
		cy.task("smtp:clear")
	})

	after(() => {
		// Leave the seed as the other specs expect it: the portal user administers nothing, and the
		// accounts this spec made are gone.
		cy.adminApi(
			seed,
			"PUT",
			`/auth/security/customers/${seed.customers.a}/users/${seed.portal_user_id}/customer-admin`,
			{
				is_customer_admin: false
			}
		)
		cy.adminApi(seed, "GET", "/auth/users").then(({ body }) => {
			const users = (body as { users: { id: number; username: string }[] }).users
			for (const user of users.filter(u => created.includes(u.username))) {
				cy.adminApi(seed, "DELETE", `/auth/delete/${user.id}`)
			}
		})
	})

	function waitForMail(to: string, attempts = 30): Cypress.Chainable<SinkMessage[]> {
		return cy.task<SinkMessage[]>("smtp:messages").then(messages => {
			const mine = messages.filter(message => message.to.includes(to))
			if (mine.length || attempts <= 1) return cy.wrap(mine)
			return cy.wait(500).then(() => waitForMail(to, attempts - 1))
		})
	}

	function signInAsColleague() {
		cy.session(`colleague-${run}`, () => {
			cy.visit("/login")
			cy.get("[data-testid=login-username] input").type(colleague.username)
			cy.get("[data-testid=login-password] input").type(colleague.password, { log: false })
			cy.get("[data-testid=login-submit]").click()
			cy.location("pathname").should("not.eq", "/login")
		})
	}

	function row(username: string) {
		return cy.get(`[data-testid=users-row][data-user="${username}"]`)
	}

	it("a customer admin finds Users in the avatar menu, with the customer's portal users", () => {
		cy.loginToPortal(seed)
		cy.visit("/overview")
		cy.get(".n-avatar:visible").first().click()
		cy.contains(".n-dropdown-option", "Users").click()
		cy.location("pathname").should("eq", "/users")
		row(seed.portal_user).within(() => {
			cy.get("[data-testid=users-tag-self]").should("have.text", "You")
			cy.get("[data-testid=users-tag-admin]").should("exist")
			// Their own account is not theirs to manage here.
			cy.get("[data-testid=users-managed-elsewhere]").should("contain", "own account")
		})
		row(colleague.username).find("[data-testid=users-actions]").should("exist")
	})

	it("invites a colleague, whose temporary password is emailed", () => {
		created.push(invited)
		cy.loginToPortal(seed)
		cy.visit("/users")
		cy.get("[data-testid=users-invite]").click()
		cy.get("[data-testid=invite-submit]").click()
		cy.get("[data-testid=invite-username-problem]").should("contain", "Enter a username")
		cy.get("[data-testid=invite-username] input").type(invited)
		cy.get("[data-testid=invite-email] input").type(`${invited}@e2e.example`)
		cy.get("[data-testid=invite-submit]").click()
		cy.get("[data-testid=temporary-password-emailed]").should("contain", `${invited}@e2e.example`)
		cy.get("[data-testid=temporary-password-value]").should("not.exist")
		waitForMail(`${invited}@e2e.example`).should("have.length", 1)
		cy.get("[data-testid=temporary-password-done]").click()
		row(invited).find("[data-testid=users-tag-password]").should("contain", "Password change pending")

		// The same name again is the API's refusal, in the dialog.
		cy.get("[data-testid=users-invite]").click()
		cy.get("[data-testid=invite-username] input").type(invited)
		cy.get("[data-testid=invite-email] input").type(`other-${invited}@e2e.example`)
		cy.get("[data-testid=invite-submit]").click()
		cy.get("[data-testid=invite-error]").should("contain", "taken")
	})

	it("disables a colleague: their open session ends saying why, and they can't sign in until enabled", () => {
		signInAsColleague()
		cy.visit("/overview")
		cy.location("pathname").should("eq", "/overview")

		cy.loginToPortal(seed)
		cy.visit("/users")
		row(colleague.username).find("[data-testid=users-toggle-disabled]").click()
		cy.contains(".n-dialog button", "Disable").click()
		row(colleague.username).find("[data-testid=users-tag-disabled]").should("contain", "Disabled")

		signInAsColleague()
		cy.visit("/overview")
		cy.location("pathname").should("eq", "/login")
		cy.get("[data-testid=login-account-disabled]").should("contain", "Your session ended because your account was disabled.")
		cy.get("[data-testid=login-username] input").type(colleague.username)
		cy.get("[data-testid=login-password] input").type(colleague.password, { log: false })
		cy.get("[data-testid=login-submit]").click()
		cy.contains("This account is disabled. Ask your organization's administrator").should("be.visible")
		cy.location("pathname").should("eq", "/login")

		cy.loginToPortal(seed)
		cy.visit("/users")
		row(colleague.username).find("[data-testid=users-toggle-disabled]").should("contain", "Enable").click()
		row(colleague.username).find("[data-testid=users-tag-disabled]").should("not.exist")
		cy.request({
			method: "POST",
			url: "/api/auth/token/customer-portal",
			form: true,
			body: { username: colleague.username, password: colleague.password }
		})
			.its("status")
			.should("eq", 200)
	})

	it("a portal user who administers nothing has no Users, and the page says it isn't theirs", () => {
		Cypress.session.clearAllSavedSessions()
		signInAsColleague()
		cy.visit("/overview")
		cy.get(".n-avatar:visible").first().click()
		cy.contains(".n-dropdown-option", "Profile").should("be.visible")
		cy.contains(".n-dropdown-option", "Users").should("not.exist")
		cy.visit("/users")
		cy.get("[data-testid=users-forbidden]").should("contain", "Only a customer administrator")
	})

	it("fits a phone: no horizontal scroll", () => {
		cy.viewport(390, 844)
		cy.loginToPortal(seed)
		cy.visit("/users")
		cy.get("[data-testid=users-row]").should("have.length.at.least", 2)
		cy.document()
			.its("documentElement")
			.should(el => {
				expect(el.scrollWidth).to.be.at.most(el.clientWidth)
			})
	})
})
