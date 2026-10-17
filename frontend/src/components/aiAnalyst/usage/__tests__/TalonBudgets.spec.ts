/**
 * The Budgets tab (decision B): each customer's daily and monthly limit, source, spent and remaining
 * as the API's strings, with warning and exhausted tags, plus the caller's own and general chat; the
 * edit dialog's validation (CoPilot's rules), its confirmation, and the PUT's payload.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import TalonBudgets from "../TalonBudgets.vue"
import { budgets, entry, refused } from "./fixtures"

const getBudgets = vi.fn()
const putBudget = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonUsage: {
			getBudgets: (...a: unknown[]) => getBudgets(...a),
			putBudget: (...a: unknown[]) => putBudget(...a)
		},
		customers: {
			getCustomers: () =>
				Promise.resolve({ data: { customers: [{ customer_code: "GLOBEX", customer_name: "Globex" }] } })
		}
	}
}))

const ModalStub = defineComponent({
	name: "Modal",
	props: { show: { type: Boolean, default: false } },
	setup:
		(props, { slots }) =>
		() =>
			props.show ? h("div", { "data-testid": "modal-stub" }, slots.default?.()) : null
})

function render() {
	return mount(TalonBudgets, { global: { stubs: { NModal: ModalStub, Modal: ModalStub } } })
}

async function chooseAmount(wrapper: ReturnType<typeof render>, win: "daily" | "monthly", amount: string) {
	await wrapper.get(`[data-testid="talon-budget-${win}"] input[value="amount"]`).setValue(true)
	await nextTick()
	await wrapper.get(`[data-testid="talon-budget-${win}-amount"] input`).setValue(amount)
	await nextTick()
}

enableAutoUnmount(afterEach)

describe("talon budgets tab", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		getBudgets.mockReset().mockResolvedValue({ data: budgets() })
		putBudget.mockReset()
	})

	it("each customer's windows with the API's strings, sources and state, plus both chats", async () => {
		const wrapper = render()
		await flushPromises()
		expect(getBudgets).toHaveBeenCalledWith(null, expect.any(AbortSignal))
		const daily = wrapper.get('[data-testid="talon-budget-row"][data-customer="ACME"][data-window="daily"]')
		expect(daily.get('[data-testid="talon-budget-limit"]').text()).toBe("$25")
		expect(daily.text()).toContain("Override")
		expect(daily.get('[data-testid="talon-budget-spent"]').text()).toBe("20.5")
		expect(daily.get('[data-testid="talon-budget-remaining"]').text()).toBe("4.5")
		expect(daily.find('[data-testid="talon-budget-warning"]').exists()).toBe(true)
		const monthly = wrapper.get('[data-testid="talon-budget-row"][data-customer="ACME"][data-window="monthly"]')
		expect(monthly.get('[data-testid="talon-budget-spent"]').text()).toBe("300.000001")
		expect(monthly.text()).toContain("Default")
		expect(monthly.find('[data-testid="talon-budget-exhausted"]').exists()).toBe(true)
		expect(wrapper.get('[data-testid="talon-budget-own-chat"]').text()).toContain("$5")
		expect(wrapper.get('[data-testid="talon-budget-general-chat"]').text()).toContain("No limit")
	})

	it("the edit dialog opens on the current values and validates as CoPilot does", async () => {
		const wrapper = render()
		await flushPromises()
		await wrapper.get('[data-testid="talon-budget-edit"]').trigger("click")
		await nextTick()
		const amount = wrapper.get('[data-testid="talon-budget-daily-amount"] input')
		expect((amount.element as HTMLInputElement).value).toBe("25")
		const save = () => wrapper.get('[data-testid="talon-budget-save"]')

		for (const bad of ["0", "-5", "1e3", "12.5000000000001", "1000000001", "12,50"]) {
			await amount.setValue(bad)
			expect(wrapper.find('[data-testid="talon-budget-daily-problem"]').exists(), bad).toBe(true)
			expect(save().attributes("disabled"), bad).toBeDefined()
		}
		await amount.setValue("12.50")
		expect(wrapper.find('[data-testid="talon-budget-daily-problem"]').exists()).toBe(false)
		expect(save().attributes("disabled")).toBeUndefined()
	})

	it("confirms before the PUT, then sends both windows as chosen", async () => {
		putBudget.mockResolvedValue({
			data: {
				customer_code: "ACME",
				daily: entry({ limit_usd: "12.5", source: "override", spent_usd: "20.5", exhausted: true }),
				monthly: entry({ window: "month", source: "unlimited" })
			}
		})
		const wrapper = render()
		await flushPromises()
		await wrapper.get('[data-testid="talon-budget-edit"]').trigger("click")
		await nextTick()
		await chooseAmount(wrapper, "daily", "12.50")
		await wrapper.get('[data-testid="talon-budget-monthly"] input[value="unlimited"]').setValue(true)
		await wrapper.get('[data-testid="talon-budget-save"]').trigger("click")
		await nextTick()
		expect(putBudget).not.toHaveBeenCalled()
		expect(wrapper.get('[data-testid="talon-budget-confirm-daily"]').text()).toBe("$12.50")
		expect(wrapper.get('[data-testid="talon-budget-confirm-monthly"]').text()).toBe("unlimited")
		await wrapper.get('[data-testid="talon-budget-confirm-button"]').trigger("click")
		await flushPromises()
		expect(putBudget).toHaveBeenCalledWith("ACME", { daily_usd: "12.50", monthly_usd: "unlimited" })
		expect(wrapper.find('[data-testid="talon-budget-dialog"]').exists()).toBe(false)
		const daily = wrapper.get('[data-testid="talon-budget-row"][data-customer="ACME"][data-window="daily"]')
		expect(daily.get('[data-testid="talon-budget-limit"]').text()).toBe("$12.5")
	})

	it('"default" sends null; a refused PUT shows its text and keeps the dialog', async () => {
		putBudget.mockRejectedValue(refused(403, "customer not accessible"))
		const wrapper = render()
		await flushPromises()
		await wrapper.get('[data-testid="talon-budget-edit"]').trigger("click")
		await nextTick()
		await wrapper.get('[data-testid="talon-budget-daily"] input[value="default"]').setValue(true)
		await wrapper.get('[data-testid="talon-budget-save"]').trigger("click")
		await nextTick()
		await wrapper.get('[data-testid="talon-budget-confirm-button"]').trigger("click")
		await flushPromises()
		expect(putBudget).toHaveBeenCalledWith("ACME", { daily_usd: null, monthly_usd: null })
		expect(wrapper.get('[data-testid="talon-budget-error"]').text()).toBe("customer not accessible")
		expect(wrapper.find('[data-testid="talon-budget-confirm"]').exists()).toBe(true)
	})

	it("a customer not listed yet can be picked and given a budget", async () => {
		putBudget.mockResolvedValue({
			data: { customer_code: "GLOBEX", daily: entry({ limit_usd: "10", source: "override" }), monthly: entry() }
		})
		const wrapper = render()
		await flushPromises()
		wrapper.findComponent({ name: "Select" }).vm.$emit("update:value", "GLOBEX")
		await nextTick()
		await wrapper.get('[data-testid="talon-budgets-pick-edit"]').trigger("click")
		await nextTick()
		await chooseAmount(wrapper, "daily", "10")
		await wrapper.get('[data-testid="talon-budget-save"]').trigger("click")
		await nextTick()
		await wrapper.get('[data-testid="talon-budget-confirm-button"]').trigger("click")
		await flushPromises()
		expect(putBudget).toHaveBeenCalledWith("GLOBEX", { daily_usd: "10", monthly_usd: null })
		expect(wrapper.find('[data-testid="talon-budget-row"][data-customer="GLOBEX"]').exists()).toBe(true)
	})
})
