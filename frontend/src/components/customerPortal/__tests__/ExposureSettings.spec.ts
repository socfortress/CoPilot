import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import ExposureSettings from "../ExposureSettings.vue"

const getCustomerExposureSettings = vi.fn()
const setCustomerExposureSettings = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		customerPortal: {
			getCustomerExposureSettings: (...args: unknown[]) => getCustomerExposureSettings(...args),
			setCustomerExposureSettings: (...args: unknown[]) => setCustomerExposureSettings(...args)
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))
const formatDate = vi.hoisted(() =>
	vi.fn((date: string, _format: string, opts?: { tz?: boolean }) => `${date}${opts?.tz ? " local" : ""}`)
)
vi.mock("@/utils/format", () => ({ formatDate }))

function settings(enabled: boolean, updatedAt: string | null = null) {
	return {
		data: {
			success: true,
			message: "",
			settings: { customer_code: "ACME", enabled, updated_at: updatedAt, updated_by: updatedAt ? 1 : null }
		}
	}
}

function render() {
	const Host = defineComponent({
		render: () => h(NMessageProvider, () => h(ExposureSettings, { customerCode: "ACME" }))
	})
	return mount(Host)
}

beforeEach(() => {
	getCustomerExposureSettings.mockReset()
	setCustomerExposureSettings.mockReset()
	formatDate.mockClear()
	auth.isAdmin = true
})

/** Customers → Customer → Exposure (#1289). */
describe("customer portal exposure settings", () => {
	it("reads the switch as off until the customer has opted in", async () => {
		getCustomerExposureSettings.mockResolvedValue(settings(false))
		const wrapper = render()
		await flushPromises()
		expect(getCustomerExposureSettings).toHaveBeenCalledWith("ACME")
		expect(wrapper.get("[data-testid=exposure-settings-state]").text()).toContain("one agent at a time")
		expect(wrapper.find("[data-testid=exposure-settings-readonly]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=exposure-settings-updated]").exists()).toBe(false)
	})

	it("lets an admin turn the page on", async () => {
		getCustomerExposureSettings.mockResolvedValue(settings(false))
		setCustomerExposureSettings.mockResolvedValue(settings(true, "2026-10-21T08:00:00"))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=exposure-settings-switch]").trigger("click")
		await flushPromises()
		expect(setCustomerExposureSettings).toHaveBeenCalledWith("ACME", { enabled: true })
		expect(wrapper.get("[data-testid=exposure-settings-state]").text()).toContain("across their agents")
	})

	it("is read-only for an analyst", async () => {
		auth.isAdmin = false
		getCustomerExposureSettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=exposure-settings-readonly]").exists()).toBe(true)
		expect(wrapper.get("[data-testid=exposure-settings-switch]").classes()).toContain("n-switch--disabled")
	})

	it("shows when it last changed in the viewer's time, the stored time being UTC", async () => {
		getCustomerExposureSettings.mockResolvedValue(settings(true, "2026-10-21T08:00:00"))
		const wrapper = render()
		await flushPromises()
		expect(formatDate).toHaveBeenCalledWith("2026-10-21T08:00:00", "YYYY-MM-DD HH:mm", { tz: true })
		expect(wrapper.get("[data-testid=exposure-settings-updated]").text()).toBe("Last changed 2026-10-21T08:00:00 local")
	})

	it("reads its help without a space before any punctuation", async () => {
		getCustomerExposureSettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=exposure-settings-help]").text()).not.toMatch(/\s[.,;:]/)
	})

	it("keeps the switch off when saving fails", async () => {
		getCustomerExposureSettings.mockResolvedValue(settings(false))
		setCustomerExposureSettings.mockRejectedValue(new Error("boom"))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=exposure-settings-switch]").trigger("click")
		await flushPromises()
		expect(wrapper.get("[data-testid=exposure-settings-state]").text()).toContain("one agent at a time")
	})
})
