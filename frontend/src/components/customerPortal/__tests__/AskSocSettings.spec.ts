import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AskSocSettings from "../AskSocSettings.vue"

const getCustomerSocRequestSettings = vi.fn()
const setCustomerSocRequestSettings = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		customerPortal: {
			getCustomerSocRequestSettings: (...args: unknown[]) => getCustomerSocRequestSettings(...args),
			setCustomerSocRequestSettings: (...args: unknown[]) => setCustomerSocRequestSettings(...args)
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))
const formatDate = vi.hoisted(() =>
	vi.fn((date: string, _format: string, opts?: { tz?: boolean }) => `${date}${opts?.tz ? " local" : ""}`)
)
vi.mock("@/utils/format", () => ({ formatDate }))

function settings(enabled: boolean, updatedAt: string | null = null, limit: number | null = null) {
	return {
		data: {
			success: true,
			message: "",
			settings: { customer_code: "ACME", enabled, daily_request_limit: limit, updated_at: updatedAt, updated_by: updatedAt ? 1 : null }
		}
	}
}

function render() {
	const Host = defineComponent({
		render: () => h(NMessageProvider, () => h(AskSocSettings, { customerCode: "ACME" }))
	})
	return mount(Host)
}

beforeEach(() => {
	getCustomerSocRequestSettings.mockReset()
	setCustomerSocRequestSettings.mockReset()
	formatDate.mockClear()
	auth.isAdmin = true
})

/** Customers → Customer → Ask the SOC (#1305). */
describe("customer portal ask the soc settings", () => {
	it("reads the switch as off until the customer has opted in", async () => {
		getCustomerSocRequestSettings.mockResolvedValue(settings(false))
		const wrapper = render()
		await flushPromises()
		expect(getCustomerSocRequestSettings).toHaveBeenCalledWith("ACME")
		expect(wrapper.get("[data-testid=ask-soc-settings-state]").text()).toContain("cannot ask the SOC")
		expect(wrapper.find("[data-testid=ask-soc-settings-readonly]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=ask-soc-settings-updated]").exists()).toBe(false)
	})

	it("lets an admin turn the page on", async () => {
		getCustomerSocRequestSettings.mockResolvedValue(settings(false))
		setCustomerSocRequestSettings.mockResolvedValue(settings(true, "2026-10-21T08:00:00"))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=ask-soc-settings-switch]").trigger("click")
		await flushPromises()
		expect(setCustomerSocRequestSettings).toHaveBeenCalledWith("ACME", { enabled: true, daily_request_limit: null })
		expect(wrapper.get("[data-testid=ask-soc-settings-state]").text()).toContain("can ask the SOC")
	})

	it("is read-only for an analyst", async () => {
		auth.isAdmin = false
		getCustomerSocRequestSettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=ask-soc-settings-readonly]").exists()).toBe(true)
		expect(wrapper.get("[data-testid=ask-soc-settings-switch]").classes()).toContain("n-switch--disabled")
	})

	it("shows when it last changed in the viewer's time, the stored time being UTC", async () => {
		getCustomerSocRequestSettings.mockResolvedValue(settings(true, "2026-10-21T08:00:00"))
		const wrapper = render()
		await flushPromises()
		expect(formatDate).toHaveBeenCalledWith("2026-10-21T08:00:00", "YYYY-MM-DD HH:mm", { tz: true })
		expect(wrapper.get("[data-testid=ask-soc-settings-updated]").text()).toBe(
			"Last changed 2026-10-21T08:00:00 local"
		)
	})

	it("reads its help without a space before any punctuation", async () => {
		getCustomerSocRequestSettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=ask-soc-settings-help]").text()).not.toMatch(/\s[.,;:]/)
	})

	it("keeps the switch off when saving fails", async () => {
		getCustomerSocRequestSettings.mockResolvedValue(settings(false))
		setCustomerSocRequestSettings.mockRejectedValue(new Error("boom"))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=ask-soc-settings-switch]").trigger("click")
		await flushPromises()
		expect(wrapper.get("[data-testid=ask-soc-settings-state]").text()).toContain("cannot ask the SOC")
	})
})

describe("customer portal ask the soc settings: the daily limit", () => {
	it("saves a limit with its own button, keeping the switch on", async () => {
		getCustomerSocRequestSettings.mockResolvedValue(settings(true))
		setCustomerSocRequestSettings.mockResolvedValue(settings(true, "2026-10-21T08:00:00", 15))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=ask-soc-settings-limit-save]").exists()).toBe(false)
		await wrapper.get("[data-testid=ask-soc-settings-limit-mode] input[value=limited]").setValue(true)
		await flushPromises()
		const input = wrapper.get("[data-testid=ask-soc-settings-limit-value] input")
		await input.setValue("15")
		await input.trigger("blur")
		await flushPromises()
		await wrapper.get("[data-testid=ask-soc-settings-limit-save]").trigger("click")
		await flushPromises()
		expect(setCustomerSocRequestSettings).toHaveBeenCalledWith("ACME", { enabled: true, daily_request_limit: 15 })
		expect(wrapper.find("[data-testid=ask-soc-settings-limit-save]").exists()).toBe(false)
	})

	it("keeps the stored limit when the switch is turned off and hides the limit", async () => {
		getCustomerSocRequestSettings.mockResolvedValue(settings(true, null, 7))
		setCustomerSocRequestSettings.mockResolvedValue(settings(false, "2026-10-21T08:00:00", 7))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=ask-soc-settings-switch]").trigger("click")
		await flushPromises()
		expect(setCustomerSocRequestSettings).toHaveBeenCalledWith("ACME", { enabled: false, daily_request_limit: 7 })
		expect(wrapper.find("[data-testid=ask-soc-settings-limit]").exists()).toBe(false)
	})
})
