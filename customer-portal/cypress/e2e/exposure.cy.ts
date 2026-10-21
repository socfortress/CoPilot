import type { PortalSeed } from "../support/e2e"
import { SCA_CHECKS, SCA_POLICIES, VULNERABILITIES } from "../support/agent-findings"
import { compliance, cveDetail, CVES, POLICY_ID, policyAgents, vulnerabilitiesPage } from "../support/exposure"

/**
 * The Exposure page (#1289): vulnerabilities and compliance across all the customer's
 * agents. The switch, the menu entry and the "not published" answer come from the real
 * backend; what Wazuh would answer is served at the network layer (`support/exposure.ts`),
 * since the e2e backend has no Wazuh.
 */
describe("exposure", () => {
	let seed: PortalSeed

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
		cy.adminApi(seed, "PUT", `/customer_portal/exposure/settings/${seed.customers.a}`, { enabled: true })
	})

	function serveWazuh() {
		cy.intercept({ method: "GET", pathname: "/api/customer_portal/exposure/vulnerabilities" }, req => {
			req.reply(vulnerabilitiesPage(seed, req.query as Record<string, string>))
		}).as("vulnerabilities")
		cy.intercept(
			{ method: "GET", pathname: `/api/customer_portal/exposure/vulnerabilities/cve/${CVES[0].cve_id}` },
			cveDetail(seed)
		).as("cve")
		cy.intercept({ method: "GET", pathname: "/api/customer_portal/exposure/compliance" }, compliance(seed)).as(
			"compliance"
		)
		cy.intercept(
			{ method: "GET", pathname: `/api/customer_portal/exposure/compliance/${POLICY_ID}/agents` },
			policyAgents(seed)
		).as("policyAgents")
	}

	it("is in the menu, and lists the CVEs counted per severity, filtered and paged in the URL", () => {
		serveWazuh()
		cy.visit("/overview")
		// The menu renders twice (sidebar and header bar layouts): use the one on screen.
		cy.get("[data-testid=nav-exposure]:visible").first().click()
		cy.location("pathname").should("eq", "/exposure")
		cy.wait("@vulnerabilities")

		const count = (level: string) => cy.get(`[data-testid=exposure-severity-${level}] [data-testid=exposure-severity-count]`)
		count("All").should("have.text", "30")
		count("Critical").should("have.text", "2")
		count("High").should("have.text", "5")
		cy.get("[data-testid=exposure-cve-row]").should("have.length", 25)
		cy.get("[data-testid=exposure-cve-row]").first().should("contain", CVES[0].cve_id).and("contain", "97.4%")
		cy.get("[data-testid=exposure-range]").should("contain", "1–25 of 30 CVEs")

		cy.get("[data-testid=exposure-pagination] .n-pagination-item").contains("2").click()
		cy.location("search").should("eq", "?page=2")
		cy.get("[data-testid=exposure-cve-row]").should("have.length", 5)

		// A severity starts again from the first page.
		cy.get("[data-testid=exposure-severity-High]").click().should("have.attr", "aria-pressed", "true")
		cy.location("search").should("eq", "?severity=High")
		cy.get("[data-testid=exposure-cve-row]").should("have.length", 5)

		// Sent once the typing stops, with the severity still on.
		cy.intercept({
			method: "GET",
			pathname: "/api/customer_portal/exposure/vulnerabilities",
			query: { search: "package-3" }
		}).as("searched")
		cy.get("[data-testid=exposure-search] input").type("package-3")
		cy.wait("@searched").its("request.query").should("include", { severity: "High", page: "1" })
		cy.get("@searched.all").should("have.length", 1)
		cy.location("search").should("eq", "?severity=High&q=package-3")

		// The filters survive a reload.
		cy.reload()
		cy.get("[data-testid=exposure-severity-High]").should("have.attr", "aria-pressed", "true")
		cy.get("[data-testid=exposure-search] input").should("have.value", "package-3")
	})

	it("a CVE opens with its agents, each a link to that agent's vulnerabilities searched for it", () => {
		serveWazuh()
		const agentPath = `/api/agents/${seed.agent_a0.agent_id}`
		cy.intercept(
			{ method: "GET", pathname: `${agentPath}/vulnerabilities/All` },
			{
				success: true,
				message: "ok",
				vulnerabilities: [...VULNERABILITIES, { ...VULNERABILITIES[0], cve: CVES[0].cve_id, title: "Linked" }]
			}
		)
		cy.visit("/exposure")
		cy.get(`[data-testid=exposure-cve-row][data-cve=${CVES[0].cve_id}]`).click()
		cy.wait("@cve")
		cy.get("[data-testid=exposure-cve-drawer]").within(() => {
			cy.get("[data-testid=exposure-cve-id]").should("have.text", CVES[0].cve_id)
			cy.get("[data-testid=exposure-cve-description]").should("contain", "A flaw in package-0")
			cy.get("[data-testid=exposure-cve-agent]").should("have.length", 1)
			cy.get("[data-testid=exposure-cve-agent-link]").should("contain", seed.agent_a0.hostname).click()
		})
		cy.location("pathname").should("eq", `/agents/${seed.agent_a0.agent_id}`)
		cy.get("[data-testid=agent-tabs] .n-tabs-tab--active").should("contain", "Vulnerabilities")
		cy.get("[data-testid=vulnerabilities-search] input").should("have.value", CVES[0].cve_id)
		cy.get("[data-testid=vulnerability-row]").should("have.length", 1).and("contain", "Linked")
	})

	it("exports the filter on screen as CSV", () => {
		serveWazuh()
		cy.intercept({ method: "GET", pathname: "/api/customer_portal/exposure/vulnerabilities/export" }, req => {
			req.reply({
				headers: { "content-type": "text/csv", "x-export-truncated": "true" },
				body: "cve_id,severity\nCVE-2026-02000,Critical\n"
			})
		}).as("export")
		cy.visit("/exposure?severity=Critical")
		cy.wait("@vulnerabilities")
		cy.get("[data-testid=exposure-export]").click()
		cy.wait("@export").its("request.query").should("include", { severity: "Critical" })
		cy.contains("The CSV holds the first 100,000 findings").should("be.visible")
	})

	it("compliance: the weakest policy first, its agents each a link to that agent's SCA on the policy", () => {
		serveWazuh()
		const agentPath = `/api/agents/${seed.agent_a0.agent_id}`
		cy.intercept({ method: "GET", pathname: `${agentPath}/sca` }, { success: true, message: "ok", sca: SCA_POLICIES })
		cy.intercept(
			{ method: "GET", pathname: `${agentPath}/sca/${POLICY_ID}` },
			{ success: true, message: "ok", sca_policy_results: SCA_CHECKS }
		).as("checks")
		cy.visit("/exposure")
		cy.get("[data-testid=exposure-tabs] .n-tabs-tab").contains("Compliance").click()
		cy.location("search").should("eq", "?tab=compliance")
		cy.wait("@compliance")

		cy.get("[data-testid=exposure-compliance-score]").should("contain", "62%")
		cy.get("[data-testid=exposure-compliance-unavailable]").should("contain", "1 agent")
		cy.get("[data-testid=exposure-policy-score]").then(scores => {
			expect([...scores].map(s => s.textContent?.trim())).to.deep.equal(["41%", "95%"])
		})

		cy.get(`[data-testid=exposure-policy-row][data-policy=${POLICY_ID}]`).click()
		cy.wait("@policyAgents")
		cy.get("[data-testid=exposure-policy-agent-link]").should("contain", seed.agent_a0.hostname).click()
		cy.location("pathname").should("eq", `/agents/${seed.agent_a0.agent_id}`)
		cy.wait("@checks")
		cy.get("[data-testid=sca-policy-name]").should("contain", "CIS Ubuntu Linux 22.04")
	})

	it("fits a phone: no horizontal scroll on either tab", () => {
		serveWazuh()
		cy.viewport(390, 844)
		cy.visit("/exposure")
		cy.get("[data-testid=exposure-cve-row]").should("have.length", 25)
		cy.document().its("documentElement").should(el => {
			expect(el.scrollWidth).to.be.at.most(el.clientWidth)
		})
		cy.visit("/exposure?tab=compliance")
		cy.get("[data-testid=exposure-policy]").should("have.length", 2)
		cy.document().its("documentElement").should(el => {
			expect(el.scrollWidth).to.be.at.most(el.clientWidth)
		})
	})

	it("without a Wazuh, says it could not read it and offers a retry (real backend)", () => {
		cy.intercept("GET", "**/api/customer_portal/exposure/vulnerabilities*").as("real")
		cy.visit("/exposure")
		cy.wait("@real").its("response.statusCode").should("eq", 200)
		cy.get("[data-testid=exposure-error]").should("contain", "could not be read from Wazuh")
		cy.get("[data-testid=exposure-severity-All] [data-testid=exposure-severity-count]").should("have.text", "—")
		cy.get("[data-testid=exposure-error] button").click()
		cy.wait("@real")
	})

	it("is offered only while the SOC publishes it for the customer (real backend)", () => {
		cy.adminApi(seed, "PUT", `/customer_portal/exposure/settings/${seed.customers.a}`, { enabled: false })
		cy.visit("/overview")
		cy.get("[data-testid=nav-sla]:visible").should("exist")
		cy.get("[data-testid=nav-exposure]").should("not.exist")

		// Opened by its address, the page says it is not published; Wazuh is never asked.
		cy.intercept("GET", "**/api/customer_portal/exposure/vulnerabilities*").as("real")
		cy.visit("/exposure")
		cy.wait("@real").its("response.body.enabled").should("eq", false)
		cy.get("[data-testid=exposure-disabled]").should("contain", "Exposure is not available yet")

		cy.adminApi(seed, "PUT", `/customer_portal/exposure/settings/${seed.customers.a}`, { enabled: true })
	})
})
