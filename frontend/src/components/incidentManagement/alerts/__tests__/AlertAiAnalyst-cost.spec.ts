/**
 * The alert's AI Analyst panel (M5-9b, decision D): with the "Talon v2" setting off it is as before
 * (Full Report and Recommended Actions only, nothing more asked); on, a "Cost & run" sub-tab for the
 * selected report's job, which follows the report picked.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import { resetTalonV2Availability } from "@/composables/useTalonV2Availability"
import AlertAiAnalyst from "../AlertAiAnalyst.vue"

const getAvailability = vi.fn()
const getJob = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonV2: { getAvailability: (signal?: AbortSignal) => getAvailability(signal) },
		talon: { getJob: (...a: unknown[]) => getJob(...a) }
	}
}))

function report(id: number, jobId: string, createdAt: string) {
	return {
		id,
		job_id: jobId,
		alert_id: 840,
		customer_code: "ACME",
		severity_assessment: "High",
		summary: `summary ${id}`,
		report_markdown: "report",
		recommended_actions: "actions",
		created_at: createdAt
	}
}

const JOB = {
	id: "copilot-inv-840-2",
	alert_id: 840,
	customer_code: "ACME",
	status: "completed",
	alert_type: null,
	triggered_by: "auto",
	template_used: null,
	created_at: "2026-10-16T08:00:00",
	started_at: null,
	completed_at: null,
	error_message: null,
	reports: [
		report(1, "copilot-inv-840-1", "2026-10-15T08:00:00Z"),
		report(2, "copilot-inv-840-2", "2026-10-16T08:00:00Z")
	]
}

const Tabs = defineComponent({
	setup:
		(_, { slots }) =>
		() =>
			h("div", { "data-testid": "tabs" }, slots.default?.())
})
const TabPane = defineComponent({
	props: { name: { type: String, default: "" }, tab: { type: String, default: "" } },
	setup:
		(props, { slots }) =>
		() =>
			h("section", { "data-pane": props.name }, [h("header", props.tab), slots.default?.()])
})
const CostStub = defineComponent({
	name: "TalonJobCostRun",
	props: { jobId: { type: String, required: true } },
	setup: props => () => h("div", { "data-testid": "cost-stub", "data-job-id": props.jobId })
})
const MarkdownStub = defineComponent({
	props: { source: { type: String, default: "" } },
	setup: props => () => h("div", props.source)
})

function render() {
	return mount(AlertAiAnalyst, {
		props: { alertId: 840 },
		global: { stubs: { Tabs, TabPane, Markdown: MarkdownStub, TalonJobCostRun: CostStub } }
	})
}

async function settle() {
	await flushPromises()
	await vi.dynamicImportSettled()
	await flushPromises()
}

enableAutoUnmount(afterEach)

describe("alert AI analyst cost and run", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetTalonV2Availability()
		getAvailability.mockReset()
		getJob.mockReset().mockResolvedValue({ data: { success: true, data: JOB } })
	})

	it("off: Full Report and Recommended Actions, as today", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false } })
		const wrapper = render()
		await settle()
		expect(wrapper.findAll("[data-pane]").map(p => p.attributes("data-pane"))).toEqual(["report", "actions"])
		expect(wrapper.find('[data-testid="cost-stub"]').exists()).toBe(false)
		expect(wrapper.text()).not.toContain("Cost & run")
	})

	it("on: a Cost & run sub-tab for the selected report's job", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true, run_view: true } })
		const wrapper = render()
		await settle()
		expect(wrapper.findAll("[data-pane]").map(p => p.attributes("data-pane"))).toEqual([
			"report",
			"actions",
			"cost"
		])
		expect(wrapper.get('[data-pane="cost"] header').text()).toBe("Cost & run")
		// The newest report is selected first.
		expect(wrapper.get('[data-testid="cost-stub"]').attributes("data-job-id")).toBe("copilot-inv-840-2")

		wrapper.findComponent({ name: "Select" }).vm.$emit("update:value", 1)
		await nextTick()
		await settle()
		expect(wrapper.get('[data-testid="cost-stub"]').attributes("data-job-id")).toBe("copilot-inv-840-1")
	})
})
