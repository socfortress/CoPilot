/**
 * The Usage tab (CoPilot M5-9b; talon-analyst FR-COST-5): it asks for the last 30 UTC days grouped by
 * customer, prefilled with the global filter's customer; shows every cost and the total exactly as
 * the API's decimal strings (0.1 and 0.2 make 0.3, never 0.30000000000000004); says when the cost
 * is incomplete or the groups truncated; tells a non-admin what they see; and refuses a range over
 * 366 days without asking.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import { useCustomerFilterStore } from "@/stores/customer-filter"
import { AuthUserRole } from "@/types/auth"
import TalonUsagePanel from "../TalonUsagePanel.vue"
import { defaultUsageRange, NON_ADMIN_USAGE_NOTE } from "../usage"
import { figures, refused, signInAs, usageReport } from "./fixtures"

const getUsage = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonUsage: { getUsage: (...a: unknown[]) => getUsage(...a) },
		customers: { getCustomers: () => Promise.resolve({ data: { customers: [] } }) }
	}
}))

const ChartStub = defineComponent({
	name: "TalonUsageChart",
	props: { report: { type: Object, required: true } },
	setup: () => () => h("div", { "data-testid": "chart-stub" })
})

function render() {
	return mount(TalonUsagePanel, { global: { stubs: { TalonUsageChart: ChartStub } } })
}

enableAutoUnmount(afterEach)

describe("talon usage tab", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		getUsage.mockReset()
	})

	it("asks for the last 30 UTC days by customer, with the global filter's customer", async () => {
		useCustomerFilterStore().setSelected(["ACME"])
		signInAs(AuthUserRole.Admin)
		getUsage.mockResolvedValue({ data: usageReport() })
		render()
		await flushPromises()
		const [from, to] = defaultUsageRange()
		expect(getUsage).toHaveBeenCalledTimes(1)
		expect(getUsage.mock.calls[0][0]).toEqual({ from, to, group_by: "customer", customer_code: "ACME" })
	})

	it("shows every cost and the total as the API's strings: 0.1 and 0.2 make 0.3", async () => {
		signInAs(AuthUserRole.Admin)
		getUsage.mockResolvedValue({ data: usageReport() })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.findAll('[data-testid="talon-usage-cost"]').map(c => c.text())).toEqual(["0.2", "0.1"])
		expect(wrapper.get('[data-testid="talon-usage-total-cost"]').text()).toBe("0.3")
		expect(wrapper.text()).not.toContain("0.30000000000000004")
		expect(wrapper.findAll('[data-testid="talon-usage-group"]').map(c => c.text())).toEqual([
			"ACME",
			"No customer (general chat)"
		])
		expect(wrapper.find('[data-testid="talon-usage-incomplete"]').exists()).toBe(false)
		expect(wrapper.find('[data-testid="talon-usage-truncated"]').exists()).toBe(false)
		expect(wrapper.find('[data-testid="chart-stub"]').exists()).toBe(true)
	})

	it("a long decimal string is shown whole, never rounded", async () => {
		signInAs(AuthUserRole.Admin)
		const total = figures("12345678.000000000001")
		getUsage.mockResolvedValue({ data: usageReport({ groups: [{ key: "ACME", ...total }], total }) })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-usage-total-cost"]').text()).toBe("12345678.000000000001")
	})

	it("says when the cost is incomplete and when groups are truncated", async () => {
		signInAs(AuthUserRole.Admin)
		getUsage.mockResolvedValue({
			data: usageReport({
				truncated: true,
				groups: [{ key: "ACME", ...figures("0.2", { cost_complete: false, unpriced_responses: 3 }) }],
				total: figures("0.3", { cost_complete: false, unpriced_responses: 3 })
			})
		})
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-usage-incomplete"]').text()).toContain("3 response(s) had no price")
		expect(wrapper.get('[data-testid="talon-usage-truncated"]').text()).toContain("the total covers every row")
		expect(wrapper.findAll('[data-testid="talon-usage-row-incomplete"]')).toHaveLength(1)
	})

	it("a non-admin is told what they see; an admin is not", async () => {
		signInAs(AuthUserRole.Analyst)
		getUsage.mockResolvedValue({ data: usageReport() })
		const analyst = render()
		await flushPromises()
		expect(analyst.get('[data-testid="talon-usage-scope-note"]').text()).toBe(NON_ADMIN_USAGE_NOTE)
		expect(NON_ADMIN_USAGE_NOTE).toBe("Investigations for your customers and your own chat.")
		analyst.unmount()

		signInAs(AuthUserRole.Admin)
		const admin = render()
		await flushPromises()
		expect(admin.find('[data-testid="talon-usage-scope-note"]').exists()).toBe(false)
	})

	it("an empty range says so", async () => {
		signInAs(AuthUserRole.Analyst)
		getUsage.mockResolvedValue({ data: usageReport({ groups: [], total: figures("0") }) })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="talon-usage-empty"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="talon-usage-table"]').exists()).toBe(false)
	})

	it("a refusal shows its fixed text", async () => {
		signInAs(AuthUserRole.Analyst)
		getUsage.mockRejectedValue(refused(503, "usage queries are busy; try again shortly"))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-usage-error"]').text()).toBe(
			"usage queries are busy; try again shortly"
		)
	})

	it("a range over 366 days is refused here, with nothing asked", async () => {
		signInAs(AuthUserRole.Admin)
		getUsage.mockResolvedValue({ data: usageReport() })
		const wrapper = render()
		await flushPromises()
		getUsage.mockClear()
		const picker = wrapper.findComponent({ name: "DatePicker" })
		picker.vm.$emit("update:formatted-value", ["2025-01-01", "2026-10-16"])
		await nextTick()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-usage-range-problem"]').text()).toBe("At most 366 days.")
		expect(getUsage).not.toHaveBeenCalled()
	})

	it("changing the grouping asks again", async () => {
		signInAs(AuthUserRole.Admin)
		getUsage.mockResolvedValue({ data: usageReport() })
		const wrapper = render()
		await flushPromises()
		wrapper.findAllComponents({ name: "Select" })[0].vm.$emit("update:value", "model")
		await flushPromises()
		expect(getUsage.mock.calls.at(-1)?.[0].group_by).toBe("model")
	})
})
