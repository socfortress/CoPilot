/**
 * One investigation's cost (decision D): the total and each run's cost as the API's strings, the
 * per-run breakdown, the stage durations in pipeline order, the incomplete flag, and the 404 and 403
 * states (a 404 is an unknown and a refused job alike).
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import TalonJobCost from "../TalonJobCost.vue"
import { investigationUsage, JOB, refused } from "./fixtures"

const getInvestigationUsage = vi.fn()

vi.mock("@/api", () => ({
	default: { talonUsage: { getInvestigationUsage: (...a: unknown[]) => getInvestigationUsage(...a) } }
}))

function render(jobId = JOB) {
	return mount(TalonJobCost, { props: { jobId } })
}

enableAutoUnmount(afterEach)

describe("talon job cost", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		getInvestigationUsage.mockReset()
	})

	it("the total, the cost per run and the stage durations", async () => {
		getInvestigationUsage.mockResolvedValue({ data: investigationUsage() })
		const wrapper = render()
		await flushPromises()
		expect(getInvestigationUsage).toHaveBeenCalledWith(JOB, expect.any(AbortSignal))
		expect(wrapper.get('[data-testid="talon-job-cost-total"]').text()).toBe("0.100412")
		const runs = wrapper.findAll('[data-testid="talon-job-cost-run"]')
		expect(runs).toHaveLength(2)
		expect(runs[0].text()).toContain("S4")
		expect(runs[0].text()).toContain("claude-haiku-5-5")
		expect(wrapper.findAll('[data-testid="talon-job-cost-run-cost"]').map(c => c.text())).toEqual([
			"0.000412",
			"0.1"
		])
		expect(wrapper.findAll('[data-testid="talon-job-cost-stage"]').map(s => s.text())).toEqual([
			"S1: 250 ms",
			"S5: 1 min 01 s",
			"S10: 1.2 s"
		])
		expect(wrapper.get('[data-testid="talon-job-cost-incomplete"]').text()).toContain("1 response(s) had no price")
	})

	it("404: no cost for this investigation, whether unknown or not visible", async () => {
		getInvestigationUsage.mockRejectedValue(refused(404, "investigation not found"))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="talon-job-cost-not-found"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="talon-job-cost-total"]').exists()).toBe(false)
	})

	it("403: the role may not see usage", async () => {
		getInvestigationUsage.mockRejectedValue(refused(403, "This role may not see Talon usage"))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="talon-job-cost-forbidden"]').exists()).toBe(true)
	})

	it("any other refusal shows its fixed text", async () => {
		getInvestigationUsage.mockRejectedValue(refused(502, "Talon request failed"))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-job-cost-error"]').text()).toBe("Talon request failed")
	})

	it("a job with no runs yet says so", async () => {
		getInvestigationUsage.mockResolvedValue({ data: investigationUsage({ runs: [], stage_durations_ms: {} }) })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="talon-job-cost-no-runs"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="talon-job-cost-stages"]').exists()).toBe(false)
	})
})
