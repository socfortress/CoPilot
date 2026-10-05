import type { IncidentReportTemplate } from "@/types/incidentReports"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import GenerateIncidentReportForm from "../GenerateIncidentReportForm.vue"

/**
 * The customer incident report can carry a "Service Level Performance" section (#1187).
 * It is opt-in, sent as `include_sla`, and unavailable on the case-centric operational
 * layout, which has no place for it.
 */

const generateReportBackground = vi.fn()
vi.mock("@/api", () => ({
	default: {
		incidentReports: { generateReportBackground: (...args: unknown[]) => generateReportBackground(...args) },
		customers: { getCustomers: () => Promise.resolve({ data: { success: true, customers: [] } }) }
	}
}))
vi.mock("@/composables/useGlobalCustomerFilter", () => ({
	useGlobalCustomerFilter: () => ({ applyGlobalCustomerPrefill: vi.fn(), globalCustomerCodes: ref([]) })
}))

function form(defaultTemplate?: IncidentReportTemplate) {
	return mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, {
					default: () => h(GenerateIncidentReportForm, { customerCode: "ACME", ...(defaultTemplate ? { defaultTemplate } : {}) })
				})
		})
	)
}

async function submit(wrapper: ReturnType<typeof form>) {
	const button = wrapper.findAll("button").find(b => /generate/i.test(b.text()))
	if (!button) throw new Error("no generate button")
	await button.trigger("click")
	await flushPromises()
	return generateReportBackground.mock.calls.at(-1)?.[0]
}

beforeEach(() => {
	setActivePinia(createPinia())
	generateReportBackground.mockReset()
	generateReportBackground.mockResolvedValue({
		data: { success: true, message: "queued", report_id: 1, customer_code: "ACME", report_name: "r" }
	})
})

describe("generateIncidentReportForm — SLA performance", () => {
	it("leaves SLA figures out unless asked", async () => {
		const wrapper = form()
		expect(wrapper.text()).toContain("SLA figures stay internal")
		expect(await submit(wrapper)).toMatchObject({ customer_code: "ACME", report_template: "full", include_sla: false })
	})

	it("sends include_sla when switched on", async () => {
		const wrapper = form()
		await wrapper.get("[data-testid=report-include-sla]").trigger("click")
		expect(wrapper.text()).toContain("Adds response and resolution times against the agreed SLA")
		expect(await submit(wrapper)).toMatchObject({ include_sla: true })
	})

	it("is unavailable on the operational layout, and never sent from it", async () => {
		const wrapper = form("operational")
		const toggle = wrapper.get("[data-testid=report-include-sla]")
		expect(toggle.classes().join(" ")).toContain("disabled")
		expect(wrapper.text()).toContain("The operational layout is case-centric and has no SLA section")
		await toggle.trigger("click")
		expect(await submit(wrapper)).toMatchObject({ report_template: "operational", include_sla: false })
	})
})
