import type { PortalSeed } from "../support/e2e"

/**
 * Asking for an AI analysis from an alert's AI Report tab (#1215): offered only once the
 * SOC allows it for the customer, confirmed before it is sent, and followed in the tab.
 *
 * The e2e backend has no Talon (its connector has no URL), so a real request ends in the
 * backend's own "could not start" answer — which is what the second test checks, end to
 * end. Only the accepted case replies to the POST in the browser, as Talon would let it.
 */
describe("asking for an AI analysis", () => {
	let seed: PortalSeed

	function settings(body: Record<string, unknown>) {
		return cy.adminApi(seed, "PUT", `/customer_portal/ai_reports/settings/${seed.customers.a}`, {
			enabled: true,
			...body
		})
	}

	function openAiReport(alertId: number) {
		cy.visit(`/alerts/${alertId}`)
		cy.contains(".n-tabs-tab", "AI Report").click()
	}

	function confirmRequest(label: "Run analysis" | "Run again") {
		cy.get("[data-testid=ai-request-button]").click()
		cy.get("[data-testid=ai-request-confirm]").should("be.visible")
		cy.contains("button", label).click()
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
		settings({ allow_customer_requests: false, daily_request_limit: null })
	})

	it("is not offered until the SOC allows it", () => {
		settings({ allow_customer_requests: false })
		openAiReport(seed.fresh_alert_id)
		cy.get("[data-testid=ai-report-empty]").should("contain", "No AI analysis has been performed")
		cy.get("[data-testid=ai-request-button]").should("not.exist")
	})

	it("reaches the backend, which says so when the AI analyst cannot start it", () => {
		settings({ allow_customer_requests: true })
		cy.intercept("POST", "**/api/customer_portal/ai_reports/alert/*/investigate").as("request")
		openAiReport(seed.fresh_alert_id)

		cy.get("[data-testid=ai-request-button]").should("contain", "Run AI analysis")
		confirmRequest("Run analysis")

		cy.wait("@request").its("response.statusCode").should("eq", 502)
		cy.get("[data-testid=ai-request-error]").should("contain", "could not start the analysis")
		// Nothing was spent: the button is still there to try again.
		cy.get("[data-testid=ai-request-button]").should("contain", "Run AI analysis").and("not.be.disabled")
	})

	it("follows an accepted request in the tab", () => {
		settings({ allow_customer_requests: true })
		cy.intercept("POST", "**/api/customer_portal/ai_reports/alert/*/investigate", {
			statusCode: 200,
			body: {
				alert_id: seed.fresh_alert_id,
				requested_at: new Date().toISOString().replace("Z", ""),
				success: true,
				message: "AI analysis requested"
			}
		}).as("request")
		openAiReport(seed.fresh_alert_id)

		confirmRequest("Run analysis")
		cy.wait("@request")
		cy.get("[data-testid=ai-report-empty]").should("contain", "AI analysis requested")
		cy.get("[data-testid=ai-request-button]").should("contain", "Analysis in progress").and("be.disabled")
	})

	it("offers to re-run an analysis that has finished", () => {
		settings({ allow_customer_requests: true })
		openAiReport(seed.ai_alert_id)
		cy.contains("High finding").should("be.visible")
		cy.get("[data-testid=ai-request-button]").should("contain", "Re-run AI analysis")
	})

	it("names the investigation's state in words, says how long it has run, and follows it to the end", () => {
		const jobId = `e2e-running-${Date.now()}`
		const job = `/ai_analyst/jobs/${jobId}`
		cy.adminApi(seed, "POST", "/ai_analyst/jobs", {
			id: jobId,
			alert_id: seed.ai_idle_alert_id,
			customer_code: seed.customers.a,
			triggered_by: "manual"
		})
		cy.adminApi(seed, "PATCH", job, { status: "running" })

		cy.clock(Date.now(), ["Date", "setInterval", "clearInterval"])
		openAiReport(seed.ai_idle_alert_id)
		cy.get("[data-testid=ai-investigation-status]").should("contain", "Analysing · <1 min")
		cy.get("[data-testid=ai-investigation-progress]").should("contain", "has been working on this alert for <1 min")

		// The SOC's analyst gives up on it; the tab notices on its next refresh.
		cy.adminApi(seed, "PATCH", job, { status: "failed", error_message: "e2e: stopped" })
		cy.tick(3 * 60_000)
		cy.get("[data-testid=ai-investigation-status]").should("contain", "Failed").and("not.contain", "min")
		cy.get("[data-testid=ai-investigation-progress]").should("not.exist")
	})
})
