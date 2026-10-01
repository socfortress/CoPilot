import type { PortalSeed } from "../support/e2e"

/**
 * An alert's Linked Cases tab (#1192): create a case from the alert, unlink it, link it
 * back. These handlers moved from `.then()` chains to async/await; the unlink confirm
 * must still close at once, not wait for the request.
 */
describe("alert linked cases", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	const linkedCasesTab = () => cy.contains(".n-tabs-tab", /^Linked Cases \(\d+\)$/)
	const linkedCount = () => linkedCasesTab().invoke("text").then(text => Number(/\((\d+)\)/.exec(text)![1]))

	it("creates a case from the alert, unlinks it and links it back", () => {
		cy.intercept("POST", "**/case/from-alert").as("create")
		let unlinkAnswered = false
		cy.intercept("POST", "**/case/alert-unlink", req =>
			req.on("response", res => {
				res.setDelay(2000)
				// Runs after the delay, when the browser is about to get the answer.
				req.on("after:response", () => (unlinkAnswered = true))
			})).as("unlink")
		cy.intercept("POST", "**/case/alert-link").as("link")

		cy.visit(`/alerts/${seed.ai_alert_id}`)
		linkedCasesTab().click()
		linkedCount().then(before => {
			cy.contains(".n-tab-pane button", /^Create Case$/).click()
			cy.wait("@create").its("response.statusCode").should("eq", 200)
			linkedCasesTab().should("contain", `(${before + 1})`)

			// Unlink: the confirm closes on click, while the (delayed) request is still running.
			cy.get(".n-tab-pane button").filter(':contains("Unlink Case")').last().click()
			cy.get(".n-popconfirm__action button").filter(':contains("Confirm")').click()
			cy.get(".n-popconfirm").should("not.exist")
			cy.then(() => expect(unlinkAnswered, "the confirm closed before the answer").to.eq(false))
			cy.wait("@unlink").its("response.statusCode").should("eq", 200)
			linkedCasesTab().should("contain", `(${before})`)

			// Link it back from the case list in the popover.
			cy.get(".n-tab-pane button").filter(':contains("Link Case")').first().click()
			cy.get(".n-popover button:not(.n-button--disabled)").filter(':contains("Link")').first().click()
			cy.wait("@link").its("response.statusCode").should("eq", 200)
			linkedCasesTab().should("contain", `(${before + 1})`)
		})
	})
})
