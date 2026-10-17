/**
 * "Cost & run": the job's cost always (with v2 on), its run timeline only when availability's
 * `run_view` says the "Talon Phoenix" connector is set up; both forgotten at logout.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { resetTalonV2Availability, useTalonV2Availability } from "@/composables/useTalonV2Availability"
import TalonJobCostRun from "../TalonJobCostRun.vue"
import { JOB } from "./fixtures"

const getAvailability = vi.fn()

vi.mock("@/api", () => ({
	default: { talonV2: { getAvailability: (signal?: AbortSignal) => getAvailability(signal) } }
}))

function stub(name: string) {
	return defineComponent({
		name,
		props: { jobId: { type: String, required: true } },
		setup: props => () => h("div", { "data-testid": name, "data-job-id": props.jobId })
	})
}

function render() {
	return mount(TalonJobCostRun, {
		props: { jobId: JOB },
		global: { stubs: { TalonJobCost: stub("TalonJobCost"), TalonRunTimeline: stub("TalonRunTimeline") } }
	})
}

enableAutoUnmount(afterEach)

describe("talon job cost and run", () => {
	beforeEach(() => {
		resetTalonV2Availability()
		getAvailability.mockReset()
	})

	it("the run timeline only with run_view", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true, run_view: true } })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="TalonJobCost"]').attributes("data-job-id")).toBe(JOB)
		expect(wrapper.get('[data-testid="TalonRunTimeline"]').attributes("data-job-id")).toBe(JOB)
	})

	it("no run_view: cost only", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true, run_view: false } })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="TalonJobCost"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="talon-run-section"]').exists()).toBe(false)
	})

	it("run_view never outlives the setting, and a reset (logout) forgets it", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false, run_view: true } })
		const { runView, refresh } = useTalonV2Availability()
		await flushPromises()
		expect(runView.value).toBe(false)

		getAvailability.mockResolvedValue({ data: { success: true, enabled: true, run_view: true } })
		await refresh()
		expect(runView.value).toBe(true)
		resetTalonV2Availability()
		expect(runView.value).toBe(false)
	})
})
