import type { PortalSeed } from "../support/e2e"

/**
 * Read-only portal users (#1312), on the real backend and the seed. The SOC makes the seeded
 * portal user read-only on customer A: they still see everything, but no control that would change
 * A's data is offered (status selects disabled, no comment box, no Ask the SOC, no Reply, no case
 * actions, no file upload, no Create case, no Generate report), the Profile and the avatar say they
 * are read-only, and a write sent anyway is refused by the server. Turned off, the controls are back.
 */
describe("read-only portal users", () => {
	let seed: PortalSeed

	function setReadOnly(readOnly: boolean) {
		return cy.adminApi(
			seed,
			"PUT",
			`/auth/security/customers/${seed.customers.a}/users/${seed.portal_user_id}/read-only`,
			{ read_only: readOnly }
		)
	}

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
			cy.adminApi(seed, "PUT", `/customer_portal/soc_requests/settings/${seed.customers.a}`, {
				enabled: true,
				daily_request_limit: null
			})
			setReadOnly(true)
		})
	})

	after(() => {
		// Leave the seed as the other specs expect it, whatever failed above.
		setReadOnly(false)
		cy.adminApi(seed, "PUT", `/customer_portal/soc_requests/settings/${seed.customers.a}`, {
			enabled: false,
			daily_request_limit: null
		})
	})

	beforeEach(() => {
		// A fresh sign-in reads /me again: the flag is read live.
		Cypress.session.clearAllSavedSessions()
		cy.loginToPortal(seed)
	})

	it("says so on the Profile and in the avatar", () => {
		cy.visit("/profile")
		cy.get("[data-testid=profile-read-only]").should("contain.text", "Read-only")
		cy.get("[data-testid=profile-role-description]").should("have.text", "Can view your organization's data but not change it.")
		cy.get("[data-testid=profile-customer-read-only]").should("have.length", 1)
		cy.get("[data-testid=toolbar-avatar-role]:visible").should("contain.text", "Read-only user")
	})

	it("shows an alert the SOC waits on without a way to change it, and the server refuses a write anyway", () => {
		cy.visit(`/alerts/${seed.waiting_alert_id}`)
		cy.get("[data-testid=waiting-on-you]").should("be.visible")
		cy.get("[data-testid=waiting-on-you-reply]").should("not.exist")
		cy.get("[data-testid=waiting-on-you-read-only]").should("contain.text", "a colleague who can change data")
		cy.get(".n-tabs-tab[data-name=ask-soc]").should("not.exist")
		cy.get(".n-base-selection").first().should("have.class", "n-base-selection--disabled")

		cy.get(".n-tabs-tab[data-name=comments]").click()
		cy.get("[data-testid=comment-input]").should("not.exist")
		cy.get("[data-testid=read-only-notice]").should("be.visible")

		// The server is what holds: a write sent without the portal's help is refused.
		cy.request({
			method: "POST",
			url: "/api/auth/token/customer-portal",
			form: true,
			body: { username: seed.portal_user, password: seed.password }
		})
			.its("body.access_token")
			.then(token =>
				cy
					.request({
						method: "PUT",
						url: "/api/incidents/db_operations/alert/status",
						body: { alert_id: seed.waiting_alert_id, status: "IN_PROGRESS" },
						headers: { Authorization: `Bearer ${token}` },
						failOnStatusCode: false
					})
					.then(response => {
						expect(response.status).to.eq(403)
						expect(response.body.message ?? response.body.detail).to.eq(
							"Your account can view this customer's data but not change it."
						)
					})
			)
	})

	it("offers no case action, file upload, Create case or Generate report", () => {
		cy.visit(`/cases/${seed.agent_a0.case_id}`)
		cy.get(".n-tabs-tab[data-name=alerts]").click()
		cy.get("[data-testid=read-only-notice]").should("be.visible")
		cy.contains("button", "Unlink").should("not.exist")
		cy.get(".n-tabs-tab[data-name=files]").click()
		cy.get(".n-upload:visible").should("not.exist")

		cy.visit("/cases")
		cy.get("[data-testid=cases-table]").should("be.visible")
		cy.get("[data-testid=create-case-button]").should("not.exist")

		cy.visit("/reports")
		cy.get("[data-testid=report-card]").should("have.length.at.least", 1)
		cy.get("[data-testid=generate-report-button]").should("not.exist")
	})

	it("gets every control back once the SOC lets them change data again", () => {
		setReadOnly(false)
		Cypress.session.clearAllSavedSessions()
		cy.loginToPortal(seed)
		cy.visit(`/alerts/${seed.waiting_alert_id}`)
		cy.get("[data-testid=waiting-on-you-reply]").should("be.visible")
		cy.get(".n-tabs-tab[data-name=ask-soc]").should("exist")
		cy.get(".n-tabs-tab[data-name=comments]").click()
		cy.get("[data-testid=comment-input]").should("be.visible")
		cy.visit("/cases")
		cy.get("[data-testid=create-case-button]").should("be.visible")
		setReadOnly(true)
	})

	it("lets a customer admin invite a colleague read-only, and allow them changes later", () => {
		const run = Date.now().toString(36)
		const auditor = `e2e_cy_ro_${run}`
		setReadOnly(false)
		cy.adminApi(seed, "PUT", `/auth/security/customers/${seed.customers.a}/users/${seed.portal_user_id}/customer-admin`, {
			is_customer_admin: true
		})
		Cypress.session.clearAllSavedSessions()
		cy.loginToPortal(seed)
		cy.task("smtp:clear")
		cy.visit("/users")
		cy.get("[data-testid=users-invite]").click()
		cy.get("[data-testid=invite-username] input").type(auditor)
		cy.get("[data-testid=invite-email] input").type(`${auditor}@e2e.example`)
		cy.get("[data-testid=invite-read-only]").click()
		cy.get("[data-testid=invite-submit]").click()

		const row = () => cy.get(`[data-testid=users-row][data-user=${auditor}]`)
		row().find("[data-testid=users-tag-readOnly]").should("contain.text", "Read-only")
		cy.get("body").type("{esc}")
		row().find("[data-testid=users-toggle-read-only]").should("have.text", "Allow changes").click()
		row().find("[data-testid=users-tag-readOnly]").should("not.exist")
		row().find("[data-testid=users-toggle-read-only]").should("have.text", "Make read-only")

		cy.adminApi(seed, "PUT", `/auth/security/customers/${seed.customers.a}/users/${seed.portal_user_id}/customer-admin`, {
			is_customer_admin: false
		})
		cy.adminApi(seed, "GET", "/auth/users").then(({ body }) => {
			const users = (body as { users: { id: number; username: string }[] }).users
			for (const user of users.filter(u => u.username === auditor)) cy.adminApi(seed, "DELETE", `/auth/delete/${user.id}`)
		})
		setReadOnly(true)
	})
})
