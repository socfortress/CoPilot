import type { PortalSeed } from "../support/e2e"

/**
 * The Audit Log page (#1298), on the real backend and the seed: the SOC appoints the seeded
 * portal user an administrator of customer A and turns the page on; they find it in the avatar
 * menu and read what happened in their tenant: their own sign-in and comment by name, the SOC's
 * status change as "SOC" (never the admin's name); an alert opens in its modal, whose header leads
 * to its page. The filters live in the URL, the CSV is the
 * filtered log, and once the SOC turns it off the entry and the page are gone.
 */
describe("audit log", () => {
	let seed: PortalSeed
	let alertId: number

	function portalToken() {
		return cy
			.request({
				method: "POST",
				url: "/api/auth/token/customer-portal",
				form: true,
				body: { username: seed.portal_user, password: seed.password }
			})
			.its("body.access_token")
	}

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
			cy.adminApi(
				seed,
				"PUT",
				`/auth/security/customers/${seed.customers.a}/users/${seed.portal_user_id}/customer-admin`,
				{ is_customer_admin: true }
			)
			cy.adminApi(seed, "PUT", `/customer_portal/audit/settings/${seed.customers.a}`, { enabled: true })

			// Something to read: the portal user comments on one of A's alerts, the SOC moves it.
			portalToken().then(token => {
				cy.request({
					url: "/api/incidents/db_operations/alerts/filter",
					qs: { page: 1, page_size: 1, customer_codes: seed.customers.a },
					headers: { Authorization: `Bearer ${token}` }
				}).then(({ body }) => {
					alertId = body.alerts[0].id
					cy.request({
						method: "POST",
						url: "/api/incidents/db_operations/alert/comment",
						body: { alert_id: alertId, comment: "E2E audit comment text", user_name: "ignored" },
						headers: { Authorization: `Bearer ${token}` }
					})
					cy.adminApi(seed, "PUT", "/incidents/db_operations/alert/status", {
						alert_id: alertId,
						status: "IN_PROGRESS"
					})
				})
			})
		})
	})

	after(() => {
		// Leave the seed as the other specs expect it, whatever failed above.
		cy.adminApi(seed, "PUT", `/customer_portal/audit/settings/${seed.customers.a}`, { enabled: false })
		cy.adminApi(
			seed,
			"PUT",
			`/auth/security/customers/${seed.customers.a}/users/${seed.portal_user_id}/customer-admin`,
			{ is_customer_admin: false }
		)
	})

	function row(action: string) {
		return cy.get(`[data-testid=audit-row][data-action="${action}"]`)
	}

	it("a customer admin finds it in the avatar menu and reads who did what", () => {
		Cypress.session.clearAllSavedSessions()
		cy.loginToPortal(seed)
		cy.visit("/overview")
		cy.get(".n-avatar:visible").first().click()
		cy.contains(".n-dropdown-option", "Audit log").click()
		cy.location("pathname").should("eq", "/audit")

		row("alert.comment_create")
			.first()
			.within(() => {
				cy.get("[data-testid=audit-actor]").should("have.text", seed.portal_user)
				cy.get("[data-testid=audit-target]").should("have.text", `Alert #${alertId}`)
			})
		row("alert.status_change")
			.first()
			.within(() => {
				cy.get("[data-testid=audit-actor]").should("have.text", "SOC")
				cy.get("[data-testid=audit-change]").should("contain", "In Progress")
				cy.get("[data-testid=audit-ip]").should("not.exist")
			})
		row("auth.login").first().find("[data-testid=audit-actor]").should("have.text", seed.portal_user)
		cy.get("[data-testid=audit-page]").should("not.contain", seed.admin)
		cy.get("[data-testid=audit-page]").should("not.contain", "E2E audit comment text")

		// The target opens the alert in its modal, without leaving the page; the modal's header leads to it.
		row("alert.comment_create").first().find("[data-testid=audit-target]").click()
		cy.contains(".n-card-header", "Alert Details").should("be.visible")
		cy.location("pathname").should("eq", "/audit")
		cy.get("[data-testid=entity-modal-page]:visible").click()
		cy.location("pathname").should("eq", `/alerts/${alertId}`)
	})

	it("filters by category in the URL, and exports what it shows", () => {
		cy.loginToPortal(seed)
		cy.visit("/audit?category=account")
		cy.get("[data-testid=audit-row]").should("have.length.at.least", 1)
		cy.get("[data-testid=audit-row]").each(entry => {
			expect(entry.attr("data-action")).to.match(/^(auth\.|user\.)/)
		})

		cy.visit("/audit")
		cy.get("[data-testid=audit-row]").should("have.length.at.least", 1)
		cy.intercept("GET", "**/api/customer_portal/audit?*category=alerts*").as("alerts")
		cy.get("[data-testid=audit-filter-category]").click()
		cy.contains(".n-base-select-option", "Alerts").click()
		cy.location("search").should("eq", "?category=alerts")
		// The rows on screen until then are the unfiltered ones.
		cy.wait("@alerts")
		cy.get("[data-testid=audit-row]").should("have.length.at.least", 1)
		cy.get("[data-testid=audit-row]").each(entry => {
			expect(entry.attr("data-action")).to.match(/^(alert\.|ai_analysis\.)/)
		})
		cy.get("[data-testid=audit-clear]").click()
		cy.location("search").should("eq", "")

		cy.intercept("GET", "**/api/customer_portal/audit/export*").as("export")
		cy.get("[data-testid=audit-export]").click()
		cy.wait("@export").then(({ response }) => {
			expect(response?.statusCode).to.eq(200)
			expect(response?.headers["x-export-truncated"]).to.eq("false")
		})
	})

	it("is gone once the SOC turns it off", () => {
		cy.adminApi(seed, "PUT", `/customer_portal/audit/settings/${seed.customers.a}`, { enabled: false })
		cy.loginToPortal(seed)
		cy.visit("/overview")
		cy.get(".n-avatar:visible").first().click()
		cy.contains(".n-dropdown-option", "Users").should("exist")
		cy.contains(".n-dropdown-option", "Audit log").should("not.exist")
		cy.visit("/audit")
		cy.get("[data-testid=audit-forbidden]").should("contain", "for your organization's administrators")
	})
})
