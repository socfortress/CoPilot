import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AgentCases from "@/components/agents/AgentDetails/AgentCases.vue"
import { scaResultLabel, severityLabel } from "@/components/agents/AgentDetails/agentFindings"
import AgentVulnerabilities from "@/components/agents/AgentDetails/AgentVulnerabilities.vue"
import { agentStatusCells, agentStatusLabel } from "@/components/agents/agentStats"
import i18n from "@/lang"

const api = vi.hoisted(() => ({ getVulnerabilities: vi.fn(), getCases: vi.fn() }))
vi.mock("@/api", () => ({ default: { agents: api } }))

function render(component: object, props: Record<string, unknown>) {
	return mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(component, props)) }), {
		global: { stubs: { CaseDetailsButton: true } }
	})
}

beforeEach(() => {
	setActivePinia(createPinia())
	api.getVulnerabilities.mockReset()
	api.getCases.mockReset()
})

/** The agents area follows the portal's language (#1310). */
describe("an agent's tabs, translated", () => {
	it("show the vulnerabilities' labels in Italian", async () => {
		i18n.global.locale.value = "it"
		api.getVulnerabilities.mockResolvedValue({ data: { vulnerabilities: [] } })
		const wrapper = render(AgentVulnerabilities, { agentId: "001", agentLabel: "web-01" })
		await flushPromises()
		expect(wrapper.get("[data-testid=vulnerabilities-empty]").text()).toContain(
			"Nessuna vulnerabilità trovata su questo agent"
		)
		expect(wrapper.get("[data-testid=vulnerabilities-severity]").text()).toContain("Critica")
		expect(wrapper.get("[data-testid=vulnerabilities-export]").text()).toContain("Esporta CSV")
	})

	it("count a case's alerts in Italian, and say who is on it", async () => {
		i18n.global.locale.value = "it"
		api.getCases.mockResolvedValue({
			data: {
				cases: [
					{ id: 7, case_name: "Phishing", case_status: "OPEN", assigned_to: null, case_creation_time: "2026-09-01T10:00:00", alerts: [{}, {}] }
				]
			}
		})
		const wrapper = render(AgentCases, { hostname: "web-01" })
		await flushPromises()
		const row = wrapper.get("[data-testid=agent-case-row]")
		expect(row.text()).toContain("#7 · 2 alert")
		expect(row.text()).toContain("non assegnato")
		expect(wrapper.text()).toContain("Casi che coinvolgono questo host")
	})

	it("name severities, results and the status cells in the language in force", () => {
		expect(severityLabel("CRITICAL")).toBe("Critical")
		i18n.global.locale.value = "it"
		expect(severityLabel("high")).toBe("Alta")
		expect(severityLabel(null)).toBe("sconosciuta")
		expect(severityLabel("Untriaged")).toBe("Untriaged")
		expect(scaResultLabel("Failed")).toBe("non superato")
		expect(agentStatusCells({ total: 3, active: 1, offline: 1, critical: 1 }).map(c => c.label)).toEqual([
			"attivi",
			"offline",
			"critici"
		])
	})

	it("name Wazuh's agent statuses in the language in force, and an unknown one as sent", () => {
		expect(agentStatusLabel("never_connected")).toBe("Never connected")
		i18n.global.locale.value = "it"
		expect(["active", "disconnected", "never_connected", "pending"].map(agentStatusLabel)).toEqual([
			"Attivo",
			"Disconnesso",
			"Mai connesso",
			"In attesa"
		])
		expect(agentStatusLabel("quarantined")).toBe("quarantined")
	})
})
