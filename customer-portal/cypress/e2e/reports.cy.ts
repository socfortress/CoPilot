import type { PortalSeed } from "../support/e2e"

/**
 * Report generation followed to the end (#1263). The first test is real all the way
 * down: the backend renders the PDF with wkhtmltopdf and stores it in the e2e MinIO
 * (cypress/README.md). The others edit the poll's answers at the network layer to reach
 * states a fast generation never shows: still running after a reload, failed, minutes in.
 */
describe("reports: generated, followed and downloaded", () => {
	let seed: PortalSeed
	const STATUS = "/api/incidents/customer_reports/status"
	const LIST = "/api/incidents/customer_reports"

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
		cy.intercept({ method: "GET", pathname: LIST }).as("list")
		cy.intercept({ method: "POST", pathname: `${LIST}/generate/background` }).as("generate")
	})

	function generate(name: string) {
		cy.visit("/reports")
		cy.wait("@list")
		cy.get("[data-testid=generate-report-button]").click()
		cy.get("[data-testid=report-name] input").type(name)
		cy.get("[data-testid=report-generate-submit]").click()
		return cy.wait("@generate").then(({ response }) => response?.body.report_id as number)
	}

	it("tells the user on another page that the report is ready, and downloads it from the notification", () => {
		cy.intercept({ method: "GET", pathname: STATUS }).as("status")
		generate("E2E weekly").then(reportId => {
			// Leave while it renders: the notification follows the user.
			cy.get("a[href='/alerts']").first().click()
			cy.location("pathname").should("eq", "/alerts")
			let listReadsOnLeaving = 0
			cy.get("@list.all").then(calls => {
				listReadsOnLeaving = calls.length
			})

			cy.wait("@status").its("request.url").should("match", new RegExp(`/status\\?ids=${reportId}$`))
			cy.contains(".n-notification", "Report ready", { timeout: 60000 }).should("contain", "E2E weekly")
			// Learnt from the light poll alone: the list was never read again once off the page.
			cy.get("@list.all").should(calls => {
				expect(calls.length).to.eq(listReadsOnLeaving)
			})

			cy.contains(".n-notification button", "Download").click()
			cy.contains(".n-notification", "Report ready").should("not.exist")
			cy.location("pathname").should("eq", "/reports")
			cy.location("search").should("eq", "")
			cy.readFile("cypress/downloads/E2E weekly.pdf", "binary", { timeout: 30000 }).should(content => {
				expect(content.slice(0, 5)).to.eq("%PDF-")
			})

			// The bell keeps the way to the file.
			cy.get("[data-testid=notifications-bell]").click()
			cy.get("[data-testid=notification-item]").first().should("contain", "Report ready").and("contain", "Download")
		})
	})

	it("keeps following a report across a reload, and says plainly when it failed", () => {
		let state: "processing" | "failed" = "processing"
		generate("E2E reloaded").then(reportId => {
			cy.intercept({ method: "GET", pathname: STATUS }, req => {
				req.reply({
					success: true,
					message: "ok",
					missing: [],
					reports: [
						{
							id: reportId,
							report_name: "E2E reloaded",
							file_name: "E2E reloaded.pdf",
							status: state,
							started_at: new Date().toISOString(),
							running_seconds: state === "processing" ? 4 : null,
							error_message: state === "failed" ? "The report could not be generated. Try again." : null
						}
					]
				})
			}).as("status")

			cy.reload()
			cy.wait("@status")
			cy.wait("@status")
			cy.contains(".n-notification", "Report").should("not.exist")

			cy.then(() => {
				state = "failed"
			})
			cy.contains(".n-notification", "Report failed", { timeout: 10000 })
				.should("contain", "The report could not be generated. Try again.")
				.and("contain", "View reports")
		})
	})

	it("says for how long a report has been generating", () => {
		cy.intercept({ method: "GET", pathname: LIST }, req => {
			req.continue(res => {
				const startedUtc = new Date(Date.now() - 3 * 60_000 - 5_000).toISOString().replace("Z", "")
				res.body.reports[0] = { ...res.body.reports[0], status: "processing", generated_at: startedUtc }
			})
		}).as("edited")
		cy.visit("/reports")
		cy.wait("@edited")
		cy.get("[data-testid=report-status]").first().should("have.text", "Generating · 3 min")
	})
})
