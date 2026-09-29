import type { PortalSeed } from "../support/e2e"

/**
 * The AI report's Markdown (#1185): loaded only when the tab opens, code highlighted by
 * the slimmed-down highlighter, and a language it does not carry shown as plain text
 * instead of breaking the report.
 */
describe("AI report", () => {
	let seed: PortalSeed

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
	})

	it("loads the Markdown renderer only when the full report opens, and highlights the code", () => {
		cy.intercept("GET", "**/Markdown.vue*").as("markdownModule")
		// Vite serves each grammar as its own pre-bundled dependency.
		cy.intercept({ method: "GET", url: /shiki_langs_/ }).as("grammars")
		cy.visit(`/alerts/${seed.ai_alert_id}`)

		cy.contains(".n-tabs-tab", "AI Report").should("be.visible")
		cy.get("@markdownModule.all").should("have.length", 0)

		cy.contains(".n-tabs-tab", "AI Report").click()
		cy.contains("High finding").should("be.visible")
		// The full report sits in a collapsed section: still nothing loaded until it opens.
		cy.get("@markdownModule.all").should("have.length", 0)

		cy.contains("Full Report").click()
		cy.get("@markdownModule.all").should("have.length.greaterThan", 0)

		// powershell is one of the bundled languages: several coloured tokens.
		cy.contains("pre.shiki", "Get-Process").find("span[style*='color']").should("have.length.greaterThan", 2)
		// python is not bundled: it falls back to plain text rather than failing the report.
		cy.contains("pre.shiki", "e2e-fallback").should("be.visible")

		// Only the grammar the report's blocks need is downloaded: never the other bundled
		// languages just because the highlighter was created.
		cy.get("@grammars.all").then(calls => {
			const grammars = (calls as unknown as Array<{ request: { url: string } }>).map(
				call => call.request.url.match(/shiki_langs_([a-z-]+)__mjs/)?.[1]
			)
			expect(grammars).to.deep.eq(["powershell"])
		})
	})
})
