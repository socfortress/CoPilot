import type { PortalSeed } from "../support/e2e"
import { SCA_CHECKS, SCA_POLICIES, VULNERABILITIES } from "../support/agent-findings"

/**
 * An agent's Vulnerabilities, SCA and Cases tabs (#1256). The agent and its cases come
 * from the real backend and database; what Wazuh would answer (vulnerabilities, SCA) is
 * served at the network layer, since the e2e backend runs without a Wazuh. Tenancy of
 * those routes is the backend's own test (tests/e2e/agent_tabs_e2e.py).
 */
describe("agent tabs: vulnerabilities, SCA and cases", () => {
	let seed: PortalSeed
	let agentPath: string
	const NOW = Date.UTC(2026, 9, 14, 12, 0, 0)

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
			agentPath = `/api/agents/${seed.agent_a0.agent_id}`
		})
	})

	beforeEach(() => {
		cy.loginToPortal(seed)
		cy.intercept({ method: "GET", pathname: `${agentPath}/vulnerabilities/All` }, { success: true, message: "ok", vulnerabilities: VULNERABILITIES }).as(
			"vulnerabilities"
		)
		cy.intercept({ method: "GET", pathname: `${agentPath}/sca` }, { success: true, message: "ok", sca: SCA_POLICIES }).as("sca")
		cy.intercept(
			{ method: "GET", pathname: `${agentPath}/sca/cis_ubuntu22-04` },
			{ success: true, message: "ok", sca_policy_results: SCA_CHECKS }
		).as("checks")
	})

	function openTab(name: string) {
		cy.get("[data-testid=agent-tabs] .n-tabs-tab").contains(name).click()
	}

	it("opens on the overview, and loads a tab only when it is first opened", () => {
		cy.visit(`/agents/${seed.agent_a0.agent_id}`)
		cy.get("[data-testid=agent-tabs]").should("be.visible")
		cy.wait(500)
		cy.get("@vulnerabilities.all").should("have.length", 0)
		cy.get("@sca.all").should("have.length", 0)

		openTab("Vulnerabilities")
		cy.wait("@vulnerabilities")
		cy.get("@sca.all").should("have.length", 0)
	})

	it("vulnerabilities: while Wazuh answers, the tab says it can take a while", () => {
		cy.intercept({ method: "GET", pathname: `${agentPath}/vulnerabilities/All` }, req => {
			req.reply({ delay: 1500, body: { success: true, message: "ok", vulnerabilities: VULNERABILITIES } })
		}).as("slowFindings")
		cy.visit(`/agents/${seed.agent_a0.agent_id}`)
		openTab("Vulnerabilities")
		cy.get("[data-testid=vulnerabilities-loading]").should("contain", "This can take up to a minute")
		cy.wait("@slowFindings")
		cy.get("[data-testid=vulnerabilities-loading]").should("not.exist")
		cy.get("[data-testid=vulnerability-row]").should("have.length", 25)
	})

	it("vulnerabilities: counted per severity, worst first, filtered, searched and paged", () => {
		cy.visit(`/agents/${seed.agent_a0.agent_id}`)
		openTab("Vulnerabilities")
		cy.wait("@vulnerabilities")

		const severity = () => cy.get("[data-testid=vulnerabilities-severity]")
		severity()
			.invoke("text")
			.should("match", /All\s*30/)
			.and("match", /Critical\s*2/)
			.and("match", /High\s*5/)
		cy.get("[data-testid=vulnerability-row]").should("have.length", 25)
		cy.get("[data-testid=vulnerabilities-range]").should("contain", "1–25 of 30")
		// Worst first: the highest-scored Critical leads.
		cy.get("[data-testid=vulnerability-row]").first().should("contain", VULNERABILITIES[0].cve)

		cy.get("[data-testid=severity-High]").click().should("have.attr", "aria-pressed", "true")
		cy.get("[data-testid=vulnerability-row]").should("have.length", 5)
		cy.get("[data-testid=vulnerabilities-range]").should("not.exist")

		cy.get("[data-testid=vulnerabilities-search] input").type("package-12")
		cy.get("[data-testid=vulnerability-row]").should("have.length", 1).and("contain", "package-12")

		cy.get("[data-testid=vulnerabilities-search] input").clear().type("nothing-like-this")
		cy.get("[data-testid=vulnerabilities-empty]").should("contain", "No vulnerability matches the filters")
	})

	it("vulnerabilities: a row opens its detail, with the references as links", () => {
		cy.visit(`/agents/${seed.agent_a0.agent_id}`)
		openTab("Vulnerabilities")
		cy.wait("@vulnerabilities")

		cy.get("[data-testid=vulnerability-row]").first().find("button").click()
		cy.get("[data-testid=vulnerability-detail]")
			.should("contain", "amd64")
			.find("a")
			.should("have.attr", "href", VULNERABILITIES[0].external_references?.[0])
			.and("have.attr", "target", "_blank")
	})

	it("vulnerabilities: the export asks for the severity on screen and saves a CSV", () => {
		cy.clock(NOW, ["Date"])
		cy.intercept({ method: "GET", pathname: `${agentPath}/csv/vulnerabilities/Critical` }, {
			body: "Severity,CVE\nCritical,CVE-2026-01000\n",
			headers: { "content-type": "text/csv" }
		}).as("csv")
		cy.visit(`/agents/${seed.agent_a0.agent_id}`)
		openTab("Vulnerabilities")
		cy.wait("@vulnerabilities")

		cy.get("[data-testid=severity-Critical]").click()
		cy.get("[data-testid=vulnerabilities-export]").click()
		cy.wait("@csv")
		cy.readFile(`cypress/downloads/${seed.agent_a0.hostname}-vulnerabilities-critical-2026-10-14-12-00-00.csv`).should(
			"contain",
			"CVE-2026-01000"
		)
	})

	it("SCA: worst policy first, its checks failed first, filtered, explained, exported, and back", () => {
		cy.clock(NOW, ["Date"])
		cy.intercept({ method: "GET", pathname: `${agentPath}/csv/sca/cis_ubuntu22-04` }, {
			body: "Title,Result\nEnsure /tmp is a separate partition,failed\n",
			headers: { "content-type": "text/csv" }
		}).as("scaCsv")
		cy.visit(`/agents/${seed.agent_a0.agent_id}`)
		openTab("SCA")
		cy.wait("@sca")

		cy.get("[data-testid=sca-policy-row]").should("have.length", 2).first().should("contain", "57%").click()
		cy.wait("@checks")
		cy.get("[data-testid=sca-policy-name]").should("contain", "CIS Ubuntu Linux 22.04")
		cy.get("[data-testid=sca-result]").invoke("text").should("match", /All\s*4/).and("match", /Failed\s*2/)
		cy.get("[data-testid=sca-check-row]").first().should("contain", "failed")

		cy.get("[data-testid=sca-result]").contains("Failed").click()
		cy.get("[data-testid=sca-check-row]").should("have.length", 2)
		cy.get("[data-testid=sca-search] input").type("AIDE")
		cy.get("[data-testid=sca-check-row]").should("have.length", 1).find("button").click()
		cy.get("[data-testid=sca-check-detail]")
			.should("contain", "What to do")
			.and("contain", "cis 1.1.2")
			// Wazuh's placeholder for an absent field is not shown as if it were content.
			.and("not.contain", "Reason not found")

		cy.get("[data-testid=sca-export]").click()
		cy.wait("@scaCsv")
		cy.readFile(`cypress/downloads/${seed.agent_a0.hostname}-sca-cis_ubuntu22-04-2026-10-14-12-00-00.csv`).should(
			"contain",
			"Ensure /tmp is a separate partition"
		)

		cy.get("[data-testid=sca-back]").click()
		cy.get("[data-testid=sca-policy-row]").should("have.length", 2)
	})

	it("cases: the agent's own case, never another customer's on the same host name, and its page", () => {
		cy.intercept({ method: "GET", pathname: `/api/agents/${seed.agent_a0.hostname}/cases` }).as("cases")
		cy.visit(`/agents/${seed.agent_a0.agent_id}`)
		openTab("Cases")
		cy.wait("@cases").its("response.statusCode").should("eq", 200)

		cy.get("[data-testid=agent-case-row]").should("have.length", 1).and("contain", `#${seed.agent_a0.case_id}`)
		cy.get("[data-testid=agent-cases]").should("not.contain", `#${seed.foreign_case_id} `)

		cy.get("[data-testid=agent-case-row]").first().find('button[aria-label="Open case page"]').click()
		cy.location("pathname").should("eq", `/cases/${seed.agent_a0.case_id}`)
	})

	it("a tab that fails says so, and the others still work", () => {
		cy.intercept({ method: "GET", pathname: `${agentPath}/vulnerabilities/All` }, {
			statusCode: 502,
			body: { detail: "Wazuh is unreachable" }
		}).as("failed")
		cy.visit(`/agents/${seed.agent_a0.agent_id}`)
		openTab("Vulnerabilities")
		cy.wait("@failed")
		cy.get("[data-testid=vulnerabilities-error]").should("contain", "Wazuh is unreachable")

		openTab("SCA")
		cy.wait("@sca")
		cy.get("[data-testid=sca-policy-row]").should("have.length", 2)
	})
})
