/**
 * The job page's "Cost & run" (M5-9b, decision D): on the page itself (`embedded=false`) with the
 * "Talon v2" setting on; never in the embedded job lists (one cost read per row), and not with the
 * setting off.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { resetTalonV2Availability } from "@/composables/useTalonV2Availability"
import JobDetails from "../JobDetails.vue"

const getAvailability = vi.fn()

vi.mock("@/api", () => ({
	default: { talonV2: { getAvailability: (signal?: AbortSignal) => getAvailability(signal) } }
}))

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
	error_message: null
}

const CostStub = defineComponent({
	name: "TalonJobCostRun",
	props: { jobId: { type: String, required: true } },
	setup: props => () => h("div", { "data-testid": "cost-stub", "data-job-id": props.jobId })
})

function render(embedded: boolean) {
	const Page = defineComponent({
		setup: () => () => h(NMessageProvider, () => h(JobDetails, { job: JOB, embedded }))
	})
	return mount(Page, { global: { stubs: { TalonJobCostRun: CostStub } } })
}

async function settle() {
	await flushPromises()
	await vi.dynamicImportSettled()
	await flushPromises()
}

enableAutoUnmount(afterEach)

describe("job details cost and run", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetTalonV2Availability()
		getAvailability.mockReset()
	})

	it("on, the job page: the job's cost and run", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		const wrapper = render(false)
		await settle()
		expect(wrapper.get('[data-testid="cost-stub"]').attributes("data-job-id")).toBe(JOB.id)
	})

	it("on, an embedded list row: nothing", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		const wrapper = render(true)
		await settle()
		expect(wrapper.find('[data-testid="cost-stub"]').exists()).toBe(false)
	})

	it("off: as before", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false } })
		const wrapper = render(false)
		await settle()
		expect(wrapper.find('[data-testid="cost-stub"]').exists()).toBe(false)
		expect(wrapper.find('[data-testid="job-cost-and-run"]').exists()).toBe(false)
	})
})
