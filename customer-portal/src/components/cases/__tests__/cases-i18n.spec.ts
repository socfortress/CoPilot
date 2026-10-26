import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import CaseTasks from "@/components/cases/CaseDetails/CaseTasks.vue"
import i18n from "@/lang"

const getCaseTasks = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { caseTemplates: { getCaseTasks } } }))

function task(id: number, status: string, extra: Record<string, unknown> = {}) {
	return {
		id,
		title: `task ${id}`,
		status,
		mandatory: false,
		template_task_id: null,
		description: null,
		guidelines: null,
		evidence_comment: null,
		completed_by: null,
		completed_at: null,
		created_by: "analyst",
		...extra
	}
}

function render() {
	return mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(CaseTasks, { caseId: 1 })) }))
}

beforeEach(() => {
	setActivePinia(createPinia())
	getCaseTasks.mockReset()
	getCaseTasks.mockResolvedValue({
		data: { tasks: [task(1, "TODO", { mandatory: true }), task(2, "DONE", { completed_by: "soc-jane" })] }
	})
})

/** The cases area follows the portal's language (#1310). */
describe("a case's tasks, translated", () => {
	it("read in English by default", async () => {
		const wrapper = render()
		await flushPromises()
		expect(wrapper.text()).toContain("Read-only view of investigation tasks performed by the SOC team on this case.")
		expect(wrapper.text()).toContain("To do")
		expect(wrapper.text()).toContain("Completed by soc-jane")
		expect(wrapper.findAll("strong").map(s => s.text())).toEqual(["analyst", "soc-jane"])
	})

	it("read in Italian when the language is Italian, names and data untouched", async () => {
		i18n.global.locale.value = "it"
		const wrapper = render()
		await flushPromises()
		expect(wrapper.text()).toContain("Vista in sola lettura delle attività di indagine svolte dal team SOC su questo caso.")
		expect(wrapper.text()).toContain("Da fare")
		expect(wrapper.text()).toContain("obbligatoria")
		expect(wrapper.text()).toContain("Completata da soc-jane")
		expect(wrapper.text()).toContain("Creata da analyst")
		expect(wrapper.text()).toContain("task 1")
		expect(wrapper.text()).not.toContain("Completed by")
	})
})
