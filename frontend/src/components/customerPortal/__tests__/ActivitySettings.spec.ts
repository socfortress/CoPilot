import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import ActivitySettings from "../ActivitySettings.vue"

const getCustomerActivitySettings = vi.fn()
const setCustomerActivitySettings = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		customerPortal: {
			getCustomerActivitySettings: (...args: unknown[]) => getCustomerActivitySettings(...args),
			setCustomerActivitySettings: (...args: unknown[]) => setCustomerActivitySettings(...args)
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
		render: () => h(NMessageProvider, () => h(ActivitySettings, { customerCode: "ACME" }))
	})
	return mount(Host)
}

beforeEach(() => {
	getCustomerActivitySettings.mockReset()
	setCustomerActivitySettings.mockReset()
	formatDate.mockClear()
	auth.isAdmin = true
})

/** Customers → Customer → Activity (#1284). */
describe("customer portal activity settings", () => {
	it("reads the switch as off until the customer has opted in", async () => {
		getCustomerActivitySettings.mockResolvedValue(settings(false))
		const wrapper = render()
		await flushPromises()
		expect(getCustomerActivitySettings).toHaveBeenCalledWith("ACME")
		expect(wrapper.get("[data-testid=activity-settings-state]").text()).toContain("stays internal")
		expect(wrapper.find("[data-testid=activity-settings-readonly]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=activity-settings-updated]").exists()).toBe(false)
	})

	it("lets an admin turn the page on", async () => {
		getCustomerActivitySettings.mockResolvedValue(settings(false))
		setCustomerActivitySettings.mockResolvedValue(settings(true, "2026-10-20T10:40:00"))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=activity-settings-switch]").trigger("click")
		await flushPromises()
		expect(setCustomerActivitySettings).toHaveBeenCalledWith("ACME", { enabled: true })
		expect(wrapper.get("[data-testid=activity-settings-state]").text()).toContain("can see what reached the SOC")
	})

	it("is read-only for an analyst", async () => {
		auth.isAdmin = false
		getCustomerActivitySettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=activity-settings-readonly]").exists()).toBe(true)
		expect(wrapper.get("[data-testid=activity-settings-switch]").classes()).toContain("n-switch--disabled")
	})

	it("shows when it last changed in the viewer's time, the stored time being UTC", async () => {
		getCustomerActivitySettings.mockResolvedValue(settings(true, "2026-10-20T10:40:00"))
		const wrapper = render()
		await flushPromises()
		expect(formatDate).toHaveBeenCalledWith("2026-10-20T10:40:00", "YYYY-MM-DD HH:mm", { tz: true })
		expect(wrapper.get("[data-testid=activity-settings-updated]").text()).toBe(
			"Last changed 2026-10-20T10:40:00 local"
		)
	})

	it("reads its help without a space before any punctuation", async () => {
		getCustomerActivitySettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		const help = wrapper.get("[data-testid=activity-settings-help]").text()
		expect(help).toContain("detections, assets and tags")
		expect(help).not.toMatch(/\s[.,;:]/)
	})

	it("keeps the switch off when saving fails", async () => {
		getCustomerActivitySettings.mockResolvedValue(settings(false))
		setCustomerActivitySettings.mockRejectedValue(new Error("boom"))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=activity-settings-switch]").trigger("click")
		await flushPromises()
		expect(wrapper.get("[data-testid=activity-settings-state]").text()).toContain("stays internal")
	})
})
