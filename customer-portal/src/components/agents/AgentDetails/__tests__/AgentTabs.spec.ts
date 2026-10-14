import type { AgentScaCheck, AgentScaPolicy, AgentVulnerability } from "@/types/agents"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider, NRadioGroup } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import AgentCases from "../AgentCases.vue"
import AgentSca from "../AgentSca.vue"
import AgentVulnerabilities from "../AgentVulnerabilities.vue"

const api = vi.hoisted(() => ({
	getVulnerabilities: vi.fn(),
	exportVulnerabilities: vi.fn(),
	getScaPolicies: vi.fn(),
	getScaChecks: vi.fn(),
	exportScaChecks: vi.fn(),
	getCases: vi.fn()
}))
const saveAs = vi.hoisted(() => vi.fn())

vi.mock("@/api", () => ({ default: { agents: api } }))
vi.mock("file-saver", () => ({ saveAs }))

function render(component: object, props: Record<string, unknown>) {
	return mount(
		defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(component, props)) }),
		// The case button opens a modal with the full case: not what these tests are about.
		{ global: { stubs: { CaseDetailsButton: { props: ["caseId"], template: "<span data-testid='case-button'>{{ caseId }}</span>" } } } }
	)
}

function vuln(cve: string, severity: string, cvss: number): AgentVulnerability {
	return {
		cve,
		severity,
		cvss3_score: cvss,
		name: `pkg-${cve}`,
		title: `${cve} title`,
		version: "1.0",
		type: null,
		architecture: null,
		status: null,
		published: null,
		detection_time: null,
		external_references: ["https://example.test/advisory"]
	}
}

function policy(policy_id: string, score: number): AgentScaPolicy {
	return {
		policy_id,
		score,
		name: policy_id,
		description: null,
		references: null,
		pass: 1,
		fail: 1,
		invalid: 0,
		total_checks: 2,
		start_scan: null,
		end_scan: null
	}
}

function check(id: number, result: string): AgentScaCheck {
	return {
		id,
		result,
		title: `check ${id}`,
		policy_id: "cis",
		description: "Description not found",
		rationale: "why",
		remediation: "do this",
		reason: null,
		command: null,
		condition: "all",
		compliance: [{ key: "cis", value: "1.1" }],
		rules: []
	}
}

/** An agent's Vulnerabilities, SCA and Cases tabs (#1256). */
describe("agent vulnerabilities", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		for (const fn of Object.values(api)) fn.mockReset()
		saveAs.mockReset()
	})

	it("loads once, counts each severity and lists the worst first", async () => {
		api.getVulnerabilities.mockResolvedValue({
			data: { vulnerabilities: [vuln("CVE-L", "Low", 2), vuln("CVE-C", "Critical", 9.8), vuln("CVE-H", "High", 8)] }
		})
		const wrapper = render(AgentVulnerabilities, { agentId: "001", agentLabel: "web-01" })
		await flushPromises()

		expect(api.getVulnerabilities).toHaveBeenCalledTimes(1)
		expect(api.getVulnerabilities.mock.calls[0]![0]).toBe("001")
		const rows = wrapper.findAll("[data-testid=vulnerability-row]")
		expect(rows.map(r => r.find(".font-mono").text())).toEqual(["CVE-C", "CVE-H", "CVE-L"])
		expect(wrapper.get("[data-testid=vulnerabilities-severity]").text().replace(/\s+/g, " ")).toContain("Critical 1")
	})

	it("a severity filter narrows the list without asking again, and the export asks for it", async () => {
		api.getVulnerabilities.mockResolvedValue({
			data: { vulnerabilities: [vuln("CVE-C", "Critical", 9.8), vuln("CVE-H", "High", 8)] }
		})
		api.exportVulnerabilities.mockResolvedValue({ data: new Blob(["csv"]) })
		const wrapper = render(AgentVulnerabilities, { agentId: "001", agentLabel: "web-01" })
		await flushPromises()

		wrapper.findComponent(NRadioGroup).vm.$emit("update:value", "High")
		await nextTick()
		expect(wrapper.findAll("[data-testid=vulnerability-row]")).toHaveLength(1)
		expect(api.getVulnerabilities).toHaveBeenCalledTimes(1)

		await wrapper.get("[data-testid=vulnerabilities-export]").trigger("click")
		await flushPromises()
		expect(api.exportVulnerabilities).toHaveBeenCalledWith("001", "High")
		expect(saveAs.mock.calls[0]![1]).toMatch(/^web-01-vulnerabilities-high-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.csv$/)
	})

	it("a row opens its detail with the references", async () => {
		api.getVulnerabilities.mockResolvedValue({ data: { vulnerabilities: [vuln("CVE-C", "Critical", 9.8)] } })
		const wrapper = render(AgentVulnerabilities, { agentId: "001", agentLabel: "web-01" })
		await flushPromises()

		await wrapper.get("[data-testid=vulnerability-row] button").trigger("click")
		expect(wrapper.get("[data-testid=vulnerability-detail] a").attributes("href")).toBe("https://example.test/advisory")
	})

	it("says when Wazuh could not be read, and that there is nothing when there is nothing", async () => {
		api.getVulnerabilities.mockRejectedValue({ response: { data: { detail: "Wazuh is unreachable" } } })
		const failed = render(AgentVulnerabilities, { agentId: "001", agentLabel: "web-01" })
		await flushPromises()
		expect(failed.get("[data-testid=vulnerabilities-error]").text()).toContain("Wazuh is unreachable")

		api.getVulnerabilities.mockResolvedValue({ data: { vulnerabilities: null } })
		const empty = render(AgentVulnerabilities, { agentId: "001", agentLabel: "web-01" })
		await flushPromises()
		expect(empty.get("[data-testid=vulnerabilities-empty]").text()).toContain("No vulnerabilities found")
	})
})

describe("agent SCA", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		for (const fn of Object.values(api)) fn.mockReset()
		saveAs.mockReset()
	})

	it("lists the worst policy first, opens its checks failed first, explains one, exports it and goes back", async () => {
		api.getScaPolicies.mockResolvedValue({ data: { sca: [policy("good", 90), policy("bad", 30)] } })
		api.getScaChecks.mockResolvedValue({ data: { sca_policy_results: [check(1, "passed"), check(2, "failed")] } })
		api.exportScaChecks.mockResolvedValue({ data: new Blob(["csv"]) })
		const wrapper = render(AgentSca, { agentId: "001", agentLabel: "web-01" })
		await flushPromises()

		const policies = wrapper.findAll("[data-testid=sca-policy-row]")
		expect(policies.map(p => p.text())).toEqual([expect.stringContaining("bad"), expect.stringContaining("good")])

		await policies[0]!.trigger("click")
		await flushPromises()
		expect(api.getScaChecks).toHaveBeenCalledWith("001", "bad", expect.any(AbortSignal))
		const checks = wrapper.findAll("[data-testid=sca-check-row]")
		expect(checks[0]!.text()).toContain("failed")

		await checks[0]!.get("button").trigger("click")
		const detail = wrapper.get("[data-testid=sca-check-detail]")
		expect(detail.text()).toContain("do this")
		expect(detail.text()).toContain("cis 1.1")
		// Wazuh's placeholder for an absent field is not content.
		expect(detail.text()).not.toContain("Description not found")

		await wrapper.get("[data-testid=sca-export]").trigger("click")
		await flushPromises()
		expect(api.exportScaChecks).toHaveBeenCalledWith("001", "bad")
		expect(saveAs.mock.calls[0]![1]).toMatch(/^web-01-sca-bad-/)

		await wrapper.get("[data-testid=sca-back]").trigger("click")
		expect(wrapper.findAll("[data-testid=sca-policy-row]")).toHaveLength(2)
	})

	it("says when no scan ran yet", async () => {
		api.getScaPolicies.mockResolvedValue({ data: { sca: null } })
		const wrapper = render(AgentSca, { agentId: "001", agentLabel: "web-01" })
		await flushPromises()
		expect(wrapper.get("[data-testid=sca-empty]").text()).toContain("No SCA scan")
	})
})

describe("agent cases", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		for (const fn of Object.values(api)) fn.mockReset()
	})

	it("lists the host's cases, each opening its own", async () => {
		api.getCases.mockResolvedValue({
			data: {
				cases: [
					{ id: 7, case_name: "Phishing on web-01", case_status: "OPEN", alerts: [{}, {}], assigned_to: null, case_creation_time: "2026-09-01T10:00:00Z" }
				]
			}
		})
		const wrapper = render(AgentCases, { hostname: "web-01" })
		await flushPromises()

		expect(api.getCases.mock.calls[0]![0]).toBe("web-01")
		const row = wrapper.get("[data-testid=agent-case-row]")
		expect(row.text()).toContain("Phishing on web-01")
		expect(row.text()).toContain("#7 · 2 alerts")
		expect(row.text()).toContain("unassigned")
		expect(row.get("[data-testid=case-button]").text()).toBe("7")
	})

	it("says when no case involves the host", async () => {
		api.getCases.mockResolvedValue({ data: { cases: [] } })
		const wrapper = render(AgentCases, { hostname: "web-01" })
		await flushPromises()
		expect(wrapper.get("[data-testid=agent-cases-empty]").text()).toContain("No case involves this host")
	})
})
