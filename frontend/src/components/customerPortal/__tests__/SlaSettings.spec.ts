import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import SlaSettings from "../SlaSettings.vue"

const getCustomerSlaSettings = vi.fn()
const setCustomerSlaSettings = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		customerPortal: {
			getCustomerSlaSettings: (...args: unknown[]) => getCustomerSlaSettings(...args),
			setCustomerSlaSettings: (...args: unknown[]) => setCustomerSlaSettings(...args)
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))

function settings(enabled: boolean) {
	return { data: { success: true, message: "", settings: { customer_code: "ACME", enabled, updated_at: null, updated_by: null } } }
}

function render() {
	const Host = defineComponent({ render: () => h(NMessageProvider, () => h(SlaSettings, { customerCode: "ACME" })) })
	return mount(Host)
}

beforeEach(() => {
	getCustomerSlaSettings.mockReset()
	setCustomerSlaSettings.mockReset()
	auth.isAdmin = true
})

describe("customer portal SLA settings", () => {
	it("reads the switch as off until the customer has opted in", async () => {
		getCustomerSlaSettings.mockResolvedValue(settings(false))
		const wrapper = render()
		await flushPromises()
		expect(getCustomerSlaSettings).toHaveBeenCalledWith("ACME")
		expect(wrapper.get("[data-testid=sla-settings-state]").text()).toContain("stay internal")
		expect(wrapper.find("[data-testid=sla-settings-readonly]").exists()).toBe(false)
	})

	it("lets an admin turn the page on", async () => {
		getCustomerSlaSettings.mockResolvedValue(settings(false))
		setCustomerSlaSettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=sla-settings-switch]").trigger("click")
		await flushPromises()
		expect(setCustomerSlaSettings).toHaveBeenCalledWith("ACME", { enabled: true })
		expect(wrapper.get("[data-testid=sla-settings-state]").text()).toContain("can see their SLA targets")
	})

	it("is read-only for an analyst", async () => {
		auth.isAdmin = false
		getCustomerSlaSettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=sla-settings-readonly]").exists()).toBe(true)
		expect(wrapper.get("[data-testid=sla-settings-switch]").classes()).toContain("n-switch--disabled")
	})
})
