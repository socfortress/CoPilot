import type { PortalSeed } from "../support/e2e"

/** What `ti:connect` put on an open alert of customer A. */
interface ThreatIntelSeed {
	alert_id: number
	iocs: { public: number; private: number; unknown: number }
	values: { public: string; private: string; unknown: string }
}

interface ThreatIntelRequest {
	method: string
	path: string
	apiKey: string | null
	value: string | null
}

/**
 * Threat Intel on the IOCs of a portal user's alert (#1318), on the real backend, with VirusTotal
 * and OpenCTI replaced by the fake cypress.config.ts runs on localhost. Opening the IOCs asks no
 * source; Check asks VirusTotal (by GET) and OpenCTI once and shows what they said, never what
 * OpenCTI marks TLP:RED; a private address is never sent; the answer is kept, so the next visit
 * asks nothing; with the customer's switch off there is no Threat Intel at all.
 */
describe("IOC enrichment", () => {
	let seed: PortalSeed
	let ti: ThreatIntelSeed

	function setEnabled(enabled: boolean) {
		return cy.adminApi(seed, "PUT", `/customer_portal/ioc_enrichment/settings/${seed.customers.a}`, {
			enabled,
			daily_lookup_limit: null
		})
	}

	const ioc = (key: keyof ThreatIntelSeed["iocs"]) => cy.get(`[data-testid=ioc-ti][data-ioc="${ti.iocs[key]}"]`)
	const requests = () => cy.task<ThreatIntelRequest[]>("ti:requests")

	function openIocs() {
		cy.visit(`/alerts/${ti.alert_id}`)
		cy.get(".n-tabs-tab[data-name=iocs]").click()
		cy.get("[data-testid=alert-ioc]").should("have.length.at.least", 3)
	}

	before(() => {
		cy.seedPortal().then(result => {
			seed = result
			cy.task<ThreatIntelSeed>("ti:connect").then(connected => {
				ti = connected
			})
			setEnabled(true)
		})
	})

	after(() => {
		setEnabled(false)
		cy.task("ti:disconnect")
	})

	beforeEach(() => {
		cy.task("ti:clear")
		cy.loginToPortal(seed)
	})

	it("checks an IOC on request and shows what Threat Intel says", () => {
		openIocs()
		ioc("public").find("[data-testid=ioc-ti-verdict]").should("contain.text", "Not checked")
		requests().should("have.length", 0)

		ioc("public").find("[data-testid=ioc-ti-check]").click()
		ioc("public").find("[data-testid=ioc-ti-verdict]").should("have.attr", "data-verdict", "malicious")
		ioc("public").find("[data-testid=ioc-ti-check]").should("not.exist")
		ioc("public").find("[data-testid=ioc-ti-next]").should("contain.text", "Can be checked again after")
		ioc("public")
			.find("[data-testid=ioc-ti-source][data-source=virustotal]")
			.should("contain.text", "Malicious")
			.and("contain.text", "Flagged by 9 of 94 engines")
		ioc("public").find("[data-testid=ioc-ti-source][data-source=opencti]").should("contain.text", "Score 80")

		requests().then(sent => {
			const virustotal = sent.filter(request => request.path.startsWith("/api/v3/"))
			expect(virustotal.map(request => [request.method, request.path, request.apiKey])).to.deep.equal([
				["GET", `/api/v3/ip_addresses/${ti.values.public}`, "e2e-key"]
			])
			const opencti = sent.filter(request => request.path === "/graphql")
			expect(opencti.map(request => [request.value, request.apiKey])).to.deep.equal([
				[ti.values.public, "Bearer e2e-key"]
			])
		})

		ioc("public").find("[data-testid=ioc-ti-toggle]").click()
		ioc("public")
			.find("[data-testid=ioc-ti-vt-link]")
			.should("have.attr", "href", `https://www.virustotal.com/gui/ip-address/${ti.values.public}`)
			.and("have.attr", "rel", "noopener noreferrer")
		ioc("public").find("[data-testid=ioc-ti-details]").should("contain.text", "Example Hosting")
		ioc("public").find("[data-testid=ioc-ti-cti-indicators]").should("contain.text", "Botnet C2 server")
		ioc("public").find("[data-testid=ioc-ti-cti-reports]").should("contain.text", "Botnet weekly")
		ioc("public").find("[data-testid=ioc-ti-cti-withheld]").should("contain.text", "1 item withheld by its sharing marking")
		cy.contains("Restricted partner report").should("not.exist")
	})

	it("never sends a private address, and reads an unknown value as not found", () => {
		openIocs()
		ioc("private").find("[data-testid=ioc-ti-kind]").should("contain.text", "never sent")
		ioc("private").find("[data-testid=ioc-ti-check]").should("not.exist")

		ioc("unknown").find("[data-testid=ioc-ti-check]").click()
		ioc("unknown").find("[data-testid=ioc-ti-verdict]").should("have.attr", "data-verdict", "not_found")
		requests().then(sent => {
			expect(sent.map(request => request.path)).to.include(`/api/v3/domains/${ti.values.unknown}`)
			expect(sent.some(request => request.path.includes(ti.values.private) || request.value === ti.values.private)).to.equal(
				false
			)
		})
	})

	it("shows the kept answer on the next visit without asking the sources again", () => {
		openIocs()
		ioc("public").find("[data-testid=ioc-ti-verdict]").should("have.attr", "data-verdict", "malicious")
		ioc("public").find("[data-testid=ioc-ti-checked]").should("contain.text", "Checked")
		ioc("public").find("[data-testid=ioc-ti-check]").should("not.exist")
		requests().should("have.length", 0)
	})

	it("has no Threat Intel when the customer has it off", () => {
		setEnabled(false)
		openIocs()
		cy.get("[data-testid=alert-ioc]").should("contain.text", ti.values.public)
		cy.get("[data-testid=ioc-ti]").should("not.exist")
		setEnabled(true)
	})
})
