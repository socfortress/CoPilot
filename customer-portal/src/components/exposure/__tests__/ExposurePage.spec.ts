import type { CveDetail, CveRow, ExposureCompliance, ExposureVulnerabilities, PolicyRow } from "@/types/exposure"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import ExposurePage from "../ExposurePage.vue"

const api = vi.hoisted(() => ({
	getVulnerabilities: vi.fn(),
	getCve: vi.fn(),
	exportVulnerabilities: vi.fn(),
	getCompliance: vi.fn(),
	getPolicyAgents: vi.fn()
}))
const saveAs = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { exposure: api } }))
vi.mock("file-saver", () => ({ saveAs }))

function cve(cve_id: string, overrides: Partial<CveRow> = {}): CveRow {
	return {
		cve_id,
		severity: "High",
		cvss: 8.1,
		epss: "0.0123",
		hosts: 2,
		packages: ["openssl"],
		first_detected: "2026-10-01T08:00:00Z",
		published: "2026-09-01T00:00:00Z",
		...overrides
	}
}

function vulnerabilities(overrides: Partial<ExposureVulnerabilities> = {}): ExposureVulnerabilities {
	return {
		enabled: true,
		customer_codes: ["ACME"],
		agents_in_scope: 3,
		severities: [
			{ severity: "Critical", cves: 1, hosts: 1, findings: 1 },
			{ severity: "High", cves: 1, hosts: 2, findings: 2 }
		],
		totals: { cves: 2, hosts: 2, findings: 3 },
		cves: [cve("CVE-2026-0001", { severity: "Critical", cvss: 9.8, hosts: 1 }), cve("CVE-2026-0002")],
		total_cves: 2,
		page: 1,
		page_size: 25,
		truncated: false,
		error: null,
		...overrides
	}
}

function detail(overrides: Partial<CveDetail> = {}): CveDetail {
	return {
		cve_id: "CVE-2026-0001",
		severity: "Critical",
		cvss: 9.8,
		epss: "0.5",
		description: "A flaw in openssl.",
		references: ["https://nvd.nist.gov/vuln/detail/CVE-2026-0001", "javascript:alert(1)"],
		published: "2026-09-01T00:00:00Z",
		agents: [
			{
				agent_id: "001",
				hostname: "web-01",
				customer_code: "ACME",
				package: "openssl",
				version: "3.0.2",
				detected: "2026-10-01T08:00:00Z"
			}
		],
		truncated: false,
		error: null,
		...overrides
	}
}

function policy(policy_id: string, average_score: number, agents_below = 0): PolicyRow {
	return {
		policy_id,
		name: `${policy_id} benchmark`,
		description: null,
		agents: 2,
		average_score,
		min_score: average_score,
		passed: 10,
		failed: 20,
		invalid: 0,
		agents_below
	}
}

function compliance(overrides: Partial<ExposureCompliance> = {}): ExposureCompliance {
	return {
		enabled: true,
		customer_codes: ["ACME"],
		agents_in_scope: 3,
		agents_assessed: 2,
		unavailable_agents: 0,
		average_score: 55,
		passed: 30,
		failed: 40,
		weak_score: 50,
		policies: [policy("cis_win", 38, 1), policy("unix_audit", 81)],
		read_at: "2026-10-20T08:00:00Z",
		error: null,
		...overrides
	}
}

const respond = <T>(data: T) => Promise.resolve({ data })

async function mountPage(query: Record<string, string> = {}) {
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: "/exposure", name: "Exposure", component: { render: () => null } },
			{ path: "/agents/:id", name: "AgentDetails", component: { render: () => null } }
		]
	})
	await router.push({ name: "Exposure", query })
	await router.isReady()
	const wrapper = mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(ExposurePage)) }), {
		global: { plugins: [router] },
		attachTo: document.body
	})
	await flushPromises()
	return { wrapper, router }
}

beforeEach(() => {
	setActivePinia(createPinia())
	for (const fn of Object.values(api)) fn.mockReset()
	saveAs.mockReset()
	api.getVulnerabilities.mockImplementation(() => respond(vulnerabilities()))
	api.getCompliance.mockImplementation(() => respond(compliance()))
})

afterEach(() => {
	document.body.innerHTML = ""
})

describe("exposure page (#1289)", () => {
	it("opens on the vulnerabilities and loads the compliance only when its tab is opened", async () => {
		const { wrapper, router } = await mountPage()
		expect(api.getVulnerabilities).toHaveBeenCalledTimes(1)
		expect(api.getCompliance).not.toHaveBeenCalled()
		expect(wrapper.findAll("[data-testid=exposure-cve-row]").map(r => r.attributes("data-cve"))).toEqual([
			"CVE-2026-0001",
			"CVE-2026-0002"
		])

		await wrapper
			.findAll(".n-tabs-tab")
			.find(t => t.text() === "Compliance")!
			.trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query).toEqual({ tab: "compliance" })
		expect(api.getCompliance).toHaveBeenCalledTimes(1)
	})

	it("opens the tab the URL names", async () => {
		const { wrapper } = await mountPage({ tab: "compliance" })
		expect(api.getCompliance).toHaveBeenCalledTimes(1)
		expect(api.getVulnerabilities).not.toHaveBeenCalled()
		expect(wrapper.findAll("[data-testid=exposure-policy]")).toHaveLength(2)
	})
})

describe("exposure vulnerabilities", () => {
	it("counts each severity, states the totals, and reads the filters from the URL", async () => {
		const { wrapper } = await mountPage({ severity: "High", q: "openssl", page: "2" })
		expect(api.getVulnerabilities).toHaveBeenCalledWith(
			{ severity: "High", search: "openssl", page: 2, pageSize: 25 },
			undefined,
			expect.any(AbortSignal)
		)
		expect(wrapper.get("[data-testid=exposure-severity-High]").attributes("aria-pressed")).toBe("true")
		expect(wrapper.get("[data-testid=exposure-severity-All] [data-testid=exposure-severity-count]").text()).toBe(
			"2"
		)
		expect(wrapper.get("[data-testid=exposure-totals]").text()).toBe("2 CVEs on 2 agents · 3 findings")
		expect((wrapper.get("[data-testid=exposure-search] input").element as HTMLInputElement).value).toBe("openssl")
	})

	it("a severity writes the URL, back on the first page, and loads again", async () => {
		const { wrapper, router } = await mountPage({ page: "3" })
		await wrapper.get("[data-testid=exposure-severity-Critical]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query).toEqual({ severity: "Critical" })
		expect(api.getVulnerabilities).toHaveBeenLastCalledWith(
			{ severity: "Critical", search: "", page: 1, pageSize: 25 },
			undefined,
			expect.any(AbortSignal)
		)
	})

	it("searches once the typing stops", async () => {
		const { wrapper, router } = await mountPage()
		await wrapper.get("[data-testid=exposure-search] input").setValue("curl")
		expect(api.getVulnerabilities).toHaveBeenCalledTimes(1)
		await new Promise(resolve => setTimeout(resolve, 350))
		await flushPromises()
		expect(router.currentRoute.value.query).toEqual({ q: "curl" })
		expect(api.getVulnerabilities).toHaveBeenCalledTimes(2)
	})

	it("follows the customer filter", async () => {
		await mountPage()
		useCustomerFilterStore().setSelected(["ACME"])
		await flushPromises()
		expect(api.getVulnerabilities).toHaveBeenLastCalledWith(expect.anything(), ["ACME"], expect.any(AbortSignal))
	})

	it("pages through more CVEs than a page holds, and says when the ranking was cut", async () => {
		api.getVulnerabilities.mockImplementation(() => respond(vulnerabilities({ total_cves: 60, truncated: true })))
		const { wrapper, router } = await mountPage()
		expect(wrapper.get("[data-testid=exposure-range]").text()).toBe("1–25 of 60 CVEs")
		expect(wrapper.find("[data-testid=exposure-truncated]").exists()).toBe(true)

		await wrapper
			.findAll("[data-testid=exposure-pagination] .n-pagination-item")
			.find(i => i.text() === "2")!
			.trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query).toEqual({ page: "2" })
	})

	it("tells an empty fleet, an empty result and a filtered-out one apart", async () => {
		api.getVulnerabilities.mockImplementation(() =>
			respond(vulnerabilities({ agents_in_scope: 0, cves: [], total_cves: 0, severities: [] }))
		)
		const empty = await mountPage()
		expect(empty.wrapper.get("[data-testid=exposure-empty]").text()).toContain("No agent to assess yet")
		empty.wrapper.unmount()

		api.getVulnerabilities.mockImplementation(() => respond(vulnerabilities({ cves: [], total_cves: 0 })))
		const filtered = await mountPage({ severity: "Low" })
		expect(filtered.wrapper.get("[data-testid=exposure-empty]").text()).toContain(
			"No vulnerability matches the filters"
		)
	})

	it("says the page is not published instead of empty figures", async () => {
		api.getVulnerabilities.mockImplementation(() => respond(vulnerabilities({ enabled: false, cves: [] })))
		const { wrapper } = await mountPage()
		expect(wrapper.find("[data-testid=exposure-disabled]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=exposure-cve-row]").exists()).toBe(false)
	})

	it("shows Wazuh's failure with a retry that loads again", async () => {
		api.getVulnerabilities.mockImplementationOnce(() =>
			respond(vulnerabilities({ error: "Could not read the vulnerabilities from Wazuh", cves: [] }))
		)
		const { wrapper } = await mountPage()
		expect(wrapper.get("[data-testid=exposure-error]").text()).toContain(
			"Could not read the vulnerabilities from Wazuh"
		)
		expect(wrapper.find("[data-testid=exposure-totals]").exists()).toBe(false)
		// No count reads as "none found" while Wazuh could not be read.
		expect(wrapper.get("[data-testid=exposure-severity-All] [data-testid=exposure-severity-count]").text()).toBe(
			"—"
		)

		await wrapper.get("[data-testid=exposure-error] button").trigger("click")
		await flushPromises()
		expect(api.getVulnerabilities).toHaveBeenCalledTimes(2)
		expect(wrapper.find("[data-testid=exposure-error]").exists()).toBe(false)
	})

	it("exports the filter on screen, and warns when the CSV was cut", async () => {
		api.exportVulnerabilities.mockResolvedValue({
			data: new Blob(["csv"]),
			headers: { "x-export-truncated": "true" }
		})
		const { wrapper } = await mountPage({ severity: "Critical", q: "openssl" })
		await wrapper.get("[data-testid=exposure-export]").trigger("click")
		await flushPromises()
		expect(api.exportVulnerabilities).toHaveBeenCalledWith({ severity: "Critical", search: "openssl" }, undefined)
		expect(saveAs.mock.calls[0]![1]).toMatch(/^vulnerabilities-critical-openssl-[\d-]+\.csv$/)
		expect(document.body.textContent).toContain("The CSV holds the first 100,000 findings")
	})

	it("says when the export failed", async () => {
		api.exportVulnerabilities.mockRejectedValue({
			response: { data: { detail: "Could not read the vulnerabilities" } }
		})
		const { wrapper } = await mountPage()
		await wrapper.get("[data-testid=exposure-export]").trigger("click")
		await flushPromises()
		expect(saveAs).not.toHaveBeenCalled()
		expect(document.body.textContent).toContain("Could not read the vulnerabilities")
	})
})

describe("exposure CVE drawer", () => {
	it("opens a CVE with its agents, each a link to that agent's vulnerabilities searched for it", async () => {
		api.getCve.mockImplementation(() => respond(detail()))
		const { wrapper } = await mountPage()
		await wrapper.get("[data-testid=exposure-cve-row][data-cve='CVE-2026-0001']").trigger("click")
		await flushPromises()

		expect(api.getCve).toHaveBeenCalledWith("CVE-2026-0001", undefined, expect.any(AbortSignal))
		const drawer = document.querySelector("[data-testid=exposure-cve-drawer]")!
		expect(drawer.querySelector("[data-testid=exposure-cve-id]")!.textContent).toBe("CVE-2026-0001")
		expect(drawer.querySelector("[data-testid=exposure-cve-epss]")!.textContent!.trim()).toBe("50.0%")
		const link = drawer.querySelector<HTMLAnchorElement>("[data-testid=exposure-cve-agent-link]")!
		expect(link.getAttribute("href")).toBe("/agents/001?tab=vulnerabilities&search=CVE-2026-0001")
		// The whole row is the link: the package and its version too, not only the name.
		expect(link.textContent).toContain("web-01")
		expect(link.textContent).toContain("openssl 3.0.2")
		// Only the web link is a link; the other reference is text.
		expect([...drawer.querySelectorAll("a[target=_blank]")].map(a => a.getAttribute("href"))).toEqual([
			"https://nvd.nist.gov/vuln/detail/CVE-2026-0001"
		])
		expect(drawer.textContent).toContain("javascript:alert(1)")
	})

	it("says when none of the agents has it any more, and when Wazuh failed", async () => {
		api.getCve.mockImplementationOnce(() => respond(detail({ agents: [] })))
		const { wrapper } = await mountPage()
		await wrapper.get("[data-testid=exposure-cve-row][data-cve='CVE-2026-0001']").trigger("click")
		await flushPromises()
		expect(document.querySelector("[data-testid=exposure-cve-none]")).not.toBeNull()

		api.getCve.mockRejectedValueOnce({ response: { data: { detail: "Vulnerability not found" } } })
		await wrapper.get("[data-testid=exposure-cve-row][data-cve='CVE-2026-0002']").trigger("click")
		await flushPromises()
		expect(document.querySelector("[data-testid=exposure-cve-error]")!.textContent).toContain(
			"Vulnerability not found"
		)
	})
})

describe("exposure compliance", () => {
	it("shows the figures, the weakest policy first, and says which agents Wazuh could not answer for", async () => {
		api.getCompliance.mockImplementation(() => respond(compliance({ unavailable_agents: 1 })))
		const { wrapper } = await mountPage({ tab: "compliance" })
		expect(
			wrapper.get("[data-testid=exposure-compliance-score] [data-testid=exposure-compliance-value]").text()
		).toBe("55%")
		expect(
			wrapper.get("[data-testid=exposure-compliance-agents] [data-testid=exposure-compliance-value]").text()
		).toBe("2 / 3")
		expect(wrapper.get("[data-testid=exposure-compliance-policies]").text()).toContain(
			"1 policy with agents below 50%"
		)
		expect(wrapper.get("[data-testid=exposure-compliance-unavailable]").text()).toContain("1 agent")
		expect(wrapper.findAll("[data-testid=exposure-policy-score]").map(s => s.text())).toEqual(["38%", "81%"])
		expect(wrapper.find("[data-testid=exposure-read-at]").exists()).toBe(true)
	})

	it("a policy opens its agents, each a link to that agent's SCA on that policy, and closes again", async () => {
		api.getPolicyAgents.mockImplementation(() =>
			respond({
				policy_id: "cis_win",
				name: "cis_win benchmark",
				error: null,
				agents: [
					{
						agent_id: "002",
						hostname: "dc-01",
						customer_code: "ACME",
						score: 38,
						passed: 10,
						failed: 20,
						invalid: 0,
						end_scan: null
					}
				]
			})
		)
		const { wrapper } = await mountPage({ tab: "compliance" })
		const row = wrapper.get("[data-testid=exposure-policy-row][data-policy=cis_win]")
		await row.trigger("click")
		await flushPromises()

		expect(api.getPolicyAgents).toHaveBeenCalledWith("cis_win", undefined, expect.any(AbortSignal))
		expect(row.attributes("aria-expanded")).toBe("true")
		expect(wrapper.get("[data-testid=exposure-policy-agent-link]").attributes("href")).toBe(
			"/agents/002?tab=sca&policy=cis_win"
		)
		// The whole row is the link, under a header that names what it lists.
		expect(wrapper.get("[data-testid=exposure-policy-agent-link]").text()).toMatch(/dc-01[\s\S]*38%[\s\S]*20/)
		expect(wrapper.get("[data-testid=exposure-policy-agents]").text()).toContain("Agents on this policy · 1")

		await row.trigger("click")
		expect(wrapper.find("[data-testid=exposure-policy-agents]").exists()).toBe(false)
	})

	it("tells no agent from no results, and shows Wazuh's failure with a retry", async () => {
		api.getCompliance.mockImplementationOnce(() =>
			respond(compliance({ agents_in_scope: 0, agents_assessed: 0, policies: [], average_score: null }))
		)
		const empty = await mountPage({ tab: "compliance" })
		expect(empty.wrapper.get("[data-testid=exposure-compliance-empty]").text()).toContain("No agent to assess yet")
		expect(
			empty.wrapper.get("[data-testid=exposure-compliance-score] [data-testid=exposure-compliance-value]").text()
		).toBe("—")
		empty.wrapper.unmount()

		api.getCompliance.mockImplementationOnce(() => Promise.reject(new Error("network down")))
		const failed = await mountPage({ tab: "compliance" })
		expect(failed.wrapper.get("[data-testid=exposure-compliance-error]").text()).toContain("network down")
		await failed.wrapper.get("[data-testid=exposure-compliance-error] button").trigger("click")
		await flushPromises()
		expect(failed.wrapper.find("[data-testid=exposure-compliance-error]").exists()).toBe(false)
		expect(failed.wrapper.findAll("[data-testid=exposure-policy]")).toHaveLength(2)
	})

	it("shows no figure when Wazuh could not be read", async () => {
		api.getCompliance.mockImplementation(() =>
			respond(compliance({ error: "Could not read the compliance from Wazuh", policies: [], failed: 0 }))
		)
		const { wrapper } = await mountPage({ tab: "compliance" })
		expect(wrapper.get("[data-testid=exposure-compliance-error]").text()).toContain("Could not read the compliance")
		expect(wrapper.findAll("[data-testid=exposure-compliance-value]").map(v => v.text())).toEqual([
			"—",
			"—",
			"—",
			"—"
		])
	})

	it("says the page is not published", async () => {
		api.getCompliance.mockImplementation(() => respond(compliance({ enabled: false, policies: [] })))
		const { wrapper } = await mountPage({ tab: "compliance" })
		expect(wrapper.find("[data-testid=exposure-disabled]").exists()).toBe(true)
	})
})
