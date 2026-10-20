import type { PortalSeed } from "../support/e2e"

/** What the SMTP sink in cypress.config.ts received. */
interface SinkMessage {
	from: string
	to: string[]
	subject: string
	data: string
}

/**
 * Portal users' notifications (#1282), against the real backend: the operator turns them on
 * for the customer, the user chooses in Profile → Notifications, the SOC asks them for a
 * reply, and the bell and their inbox say so. Emails land in the SMTP sink Cypress runs
 * (the backend's SMTP_HOST points at it, see scripts/e2e.sh).
 */
describe("portal notifications", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
			cy.adminApi(seed, "PUT", `/customer_portal/notifications/settings/${seed.customers.a}`, { enabled: true })
		})
	})

	beforeEach(() => {
		cy.task("smtp:clear")
		cy.loginToPortal(seed)
	})

	after(() => {
		// Leave the seed as the other specs expect it: notifications off.
		cy.adminApi(seed, "PUT", `/customer_portal/notifications/settings/${seed.customers.a}`, { enabled: false })
		cy.adminApi(seed, "PUT", "/incidents/db_operations/alert/status", { alert_id: seed.fresh_alert_id, status: "OPEN" })
	})

	/** The sink's messages for an address, waited for: the backend sends in the background. */
	function waitForMail(to: string, attempts = 30): Cypress.Chainable<SinkMessage[]> {
		return cy.task<SinkMessage[]>("smtp:messages").then(messages => {
			const mine = messages.filter(message => message.to.includes(to))
			if (mine.length || attempts <= 1) return cy.wrap(mine)
			return cy.wait(500).then(() => waitForMail(to, attempts - 1))
		})
	}

	/** The portal user's own choices, set through the API as that user. */
	function setPreferences(preferences: object[]) {
		cy.request({
			method: "POST",
			url: "/api/auth/token/customer-portal",
			form: true,
			body: { username: seed.portal_user, password: seed.password }
		}).then(({ body }) =>
			cy.request({
				method: "PUT",
				url: "/api/customer_portal/notifications/preferences",
				body: { preferences },
				headers: { Authorization: `Bearer ${body.access_token}` }
			})
		)
	}

	function setAlertStatus(status: string) {
		cy.adminApi(seed, "PUT", "/incidents/db_operations/alert/status", { alert_id: seed.fresh_alert_id, status })
	}

	it("lets the user choose, in Profile → Notifications, and keeps the choice", () => {
		cy.visit("/profile?tab=notifications")
		cy.get("[data-testid=profile-tab-notifications]").should("be.visible")
		cy.get("[data-testid=notification-preferences]").should("be.visible")
		cy.get("[data-testid=notification-preferences-save]").should("be.disabled")

		cy.get("[data-testid=notification-pref-waiting_on_you-email]").click()
		cy.contains(".n-base-select-option", "Immediately").click()
		cy.get("[data-testid=notification-pref-case_closed-in-app]").click()
		cy.get("[data-testid=notification-preferences-save]").should("not.be.disabled").click()
		cy.get("[data-testid=notification-preferences-save]").should("be.disabled")

		cy.reload()
		cy.get("[data-testid=notification-pref-waiting_on_you-email]").should("contain.text", "Immediately")
		cy.get("[data-testid=notification-pref-case_closed-in-app]").should("have.attr", "aria-checked", "false")
	})

	it("tells the user in the bell and by email when the SOC waits on them, and opens the alert", () => {
		setPreferences([{ event: "waiting_on_you", in_app: true, email: "immediate", min_severity: null }])
		setAlertStatus("PENDING_CUSTOMER")

		cy.visit("/overview")
		cy.get("[data-testid=notifications-bell]").should("have.attr", "data-unread", "true").click()
		cy.contains("[data-testid=notification-item]", "The SOC is waiting on your reply").should("be.visible").click()
		cy.location("pathname").should("eq", `/alerts/${seed.fresh_alert_id}`)
		cy.get("[data-testid=notifications-bell]").should("have.attr", "data-unread", "false")

		waitForMail(`${seed.portal_user}@e2e.example`).then(mail => {
			expect(mail, "one email").to.have.length(1)
			expect(mail[0]!.subject).to.contain("The SOC is waiting on your reply")
			expect(mail[0]!.data).to.contain(`/alerts/${seed.fresh_alert_id}`)
		})
	})

	it("takes the bell back to the session's own list once the customer's notifications are off", () => {
		cy.adminApi(seed, "PUT", `/customer_portal/notifications/settings/${seed.customers.a}`, { enabled: false })
		cy.visit("/profile")
		cy.get("[data-testid=profile-tab-notifications]").should("not.exist")
		cy.get("[data-testid=notifications-bell]").click()
		cy.contains("There is no notification").should("be.visible")
		cy.adminApi(seed, "PUT", `/customer_portal/notifications/settings/${seed.customers.a}`, { enabled: true })
	})
})
