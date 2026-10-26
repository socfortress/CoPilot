import type { PortalSeed } from "../support/e2e"

/**
 * "Ask the SOC" on the portal's alerts and cases (#1305), against the real backend: offered
 * only while the SOC allows it for the customer, a question becomes a comment signed by the
 * user (on the alert's open case, a case made from the alert, or the alert itself), the
 * backend's refusals are shown as they are, and a SOC comment answers it.
 */
describe("asking the SOC", () => {
	let seed: PortalSeed

	function settings(enabled: boolean) {
		return cy.adminApi(seed, "PUT", `/customer_portal/soc_requests/settings/${seed.customers.a}`, {
			enabled,
			daily_request_limit: null
		})
	}

	function openAskTab(path: string) {
		cy.visit(path)
		cy.contains(".n-tabs-tab", "Ask the SOC").click()
		cy.get("[data-testid=ask-soc-form]").should("be.visible")
	}

	function ask(question: string) {
		cy.get("[data-testid=ask-soc-question] textarea").type(question)
		cy.get("[data-testid=ask-soc-send]").click()
	}

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	after(() => {
		// Leave the seed as the other specs expect it, whatever failed above.
		settings(false)
	})

	it("is not offered until the SOC allows it", () => {
		settings(false)
		cy.visit(`/alerts/${seed.fresh_alert_id}`)
		cy.contains(".n-tabs-tab", "Overview").should("be.visible")
		cy.contains(".n-tabs-tab", "Ask the SOC").should("not.exist")
	})

	it("asks on the alert itself, then refuses a second question within 10 minutes", () => {
		settings(true)
		cy.intercept("POST", "**/api/customer_portal/soc_requests/alert/*").as("ask")
		openAskTab(`/alerts/${seed.fresh_alert_id}`)
		cy.get("[data-testid=ask-soc-empty]").should("contain", "No question asked about this alert yet.")

		// Nothing is sent without a question.
		cy.get("[data-testid=ask-soc-send]").click()
		cy.get("[data-testid=ask-soc-problem]").should("contain", "Write your question for the SOC")

		cy.get("[data-testid=ask-soc-urgency]").contains("High").click()
		cy.get("[data-testid=ask-soc-target-alert]").click()
		ask("Is this sign-in from our VPN?")
		cy.wait("@ask").its("request.body").should("deep.equal", {
			question: "Is this sign-in from our VPN?",
			urgency: "high",
			target: "alert"
		})
		cy.get("[data-testid=ask-soc-request]")
			.should("have.length", 1)
			.first()
			.should("contain", "Waiting for the SOC")
			.and("contain", "Urgency: High")
			.and("contain", "Is this sign-in from our VPN?")
		// It is a comment on the alert, signed by the user.
		cy.contains(".n-tabs-tab", "Comments (1)").click()
		cy.contains("Question for the SOC (urgency: High)").should("be.visible")

		cy.contains(".n-tabs-tab", "Ask the SOC").click()
		ask("And this one?")
		cy.wait("@ask").its("response.statusCode").should("eq", 429)
		cy.get("[data-testid=ask-soc-error]").should("contain", "ask again in")
		cy.get("[data-testid=ask-soc-request]").should("have.length", 1)
	})

	it("is answered by the SOC's comment", () => {
		settings(true)
		cy.adminApi(seed, "POST", "/incidents/db_operations/alert/comment", {
			alert_id: seed.fresh_alert_id,
			comment: "Yes, that is your VPN's exit address.",
			user_name: "ignored"
		})
		openAskTab(`/alerts/${seed.fresh_alert_id}`)
		cy.get("[data-testid=ask-soc-request]").first().should("contain", "Answered").and("contain", "answered")
	})

	it("goes on the alert's open case by default", () => {
		settings(true)
		openAskTab(`/alerts/${seed.cased_alert_id}`)
		cy.get("[data-testid=ask-soc-target-case]").should("contain", `Add to case #${seed.agent_a0.case_id}`)
		ask("Can we close this?")
		cy.get("[data-testid=ask-soc-request]")
			.first()
			.should("contain", "Waiting for the SOC")
			.and("contain", `On case #${seed.agent_a0.case_id}`)

		// The case shows it too, as asked from the alert.
		openAskTab(`/cases/${seed.agent_a0.case_id}`)
		cy.get("[data-testid=ask-soc-target]").should("not.exist")
		cy.get("[data-testid=ask-soc-request]").first().should("contain", `Asked from alert #${seed.cased_alert_id}`)
	})

	it("opens a case from an alert that has none", () => {
		settings(true)
		openAskTab(`/alerts/${seed.ai_idle_alert_id}`)
		cy.contains(".n-tabs-tab", "Linked Cases (0)").should("exist")
		cy.get("[data-testid=ask-soc-target-case]").should("contain", "Open a case from this alert")
		ask("Please look into this host.")
		cy.get("[data-testid=ask-soc-request]").first().should("contain", "On case #")
		cy.contains(".n-tabs-tab", "Linked Cases (1)").should("exist")
	})

	it("hands a case the SOC waits on back to it", () => {
		settings(true)
		openAskTab(`/cases/${seed.waiting_case_id}`)
		cy.get("[data-testid=waiting-on-you]").should("be.visible")
		ask("Here is the answer you asked for, and a question.")
		cy.get("[data-testid=ask-soc-request]").should("have.length", 1)
		cy.get("[data-testid=waiting-on-you]").should("not.exist")
	})
})
