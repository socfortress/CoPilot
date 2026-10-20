import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import NotificationSettings from "../NotificationSettings.vue"

const getCustomerNotificationSettings = vi.fn()
const setCustomerNotificationSettings = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		customerPortal: {
			getCustomerNotificationSettings: (...args: unknown[]) => getCustomerNotificationSettings(...args),
			setCustomerNotificationSettings: (...args: unknown[]) => setCustomerNotificationSettings(...args)
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))

function response(enabled: boolean, over: Record<string, unknown> = {}) {
	return {
		data: {
			success: true,
			message: "",
			settings: { customer_code: "ACME", enabled, updated_at: null, updated_by: null },
			email_configured: true,
			digest_hour_utc: 7,
			...over
		}
	}
}

function render() {
	const Host = defineComponent({
		render: () => h(NMessageProvider, () => h(NotificationSettings, { customerCode: "ACME" }))
	})
	return mount(Host)
}

beforeEach(() => {
	getCustomerNotificationSettings.mockReset()
	setCustomerNotificationSettings.mockReset()
	auth.isAdmin = true
})

describe("customer portal notification settings (#1282)", () => {
	it("reads the switch as off until an admin turns it on, with the digest hour", async () => {
		getCustomerNotificationSettings.mockResolvedValue(response(false))
		const wrapper = render()
		await flushPromises()
		expect(getCustomerNotificationSettings).toHaveBeenCalledWith("ACME")
		expect(wrapper.get("[data-testid=notification-settings-state]").text()).toContain("receive no notifications")
		expect(wrapper.get("[data-testid=notification-settings-digest-hour]").text()).toBe("07:00 UTC")
		expect(wrapper.find("[data-testid=notification-settings-no-smtp]").exists()).toBe(false)
	})

	it("lets an admin turn it on", async () => {
		getCustomerNotificationSettings.mockResolvedValue(response(false))
		setCustomerNotificationSettings.mockResolvedValue(response(true))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=notification-settings-switch]").trigger("click")
		await flushPromises()
		expect(setCustomerNotificationSettings).toHaveBeenCalledWith("ACME", { enabled: true })
		expect(wrapper.get("[data-testid=notification-settings-state]").text()).toContain("Profile → Notifications")
	})

	it("is read-only for an analyst", async () => {
		auth.isAdmin = false
		getCustomerNotificationSettings.mockResolvedValue(response(true))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=notification-settings-readonly]").exists()).toBe(true)
		expect(wrapper.get("[data-testid=notification-settings-switch]").classes()).toContain("n-switch--disabled")
	})

	it("says when email cannot go out, and at which hour the summary does", async () => {
		getCustomerNotificationSettings.mockResolvedValue(response(true, { email_configured: false, digest_hour_utc: 18 }))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=notification-settings-no-smtp]").text()).toContain("bell only")
		expect(wrapper.get("[data-testid=notification-settings-digest-hour]").text()).toBe("18:00 UTC")
	})
})
