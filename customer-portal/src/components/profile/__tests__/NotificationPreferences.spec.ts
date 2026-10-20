import type { NotificationPreference } from "@/types/notifications"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { useServerNotifications } from "@/composables/common/useServerNotifications"
import NotificationPreferences from "../NotificationPreferences.vue"

const api = vi.hoisted(() => ({
	getAvailability: vi.fn(),
	getPreferences: vi.fn(),
	setPreferences: vi.fn(),
	list: vi.fn(),
	unreadCount: vi.fn(),
	markRead: vi.fn()
}))
vi.mock("@/api", () => ({ default: { notifications: api } }))

const DEFAULTS: NotificationPreference[] = [
	{ event: "alert_created", in_app: true, email: "off", min_severity: "High" },
	{ event: "waiting_on_you", in_app: true, email: "off", min_severity: null },
	{ event: "case_closed", in_app: true, email: "off", min_severity: null },
	{ event: "report_ready", in_app: true, email: "off", min_severity: null }
]

function availability(emailAvailable: boolean, reason: string | null = null) {
	return Promise.resolve({
		data: { enabled: true, email_available: emailAvailable, email_unavailable_reason: reason, digest_hour_utc: 7 }
	})
}

function render() {
	const Host = defineComponent({ render: () => h(NMessageProvider, () => h(NotificationPreferences)) })
	return mount(Host, { attachTo: document.body })
}

beforeEach(() => {
	Object.values(api).forEach(fn => fn.mockReset())
	useServerNotifications().reset()
	api.getPreferences.mockResolvedValue({ data: { preferences: DEFAULTS } })
})

/** Profile → Notifications (#1282). */
describe("notification preferences", () => {
	it("lists every event with its choices, nothing to save yet", async () => {
		api.getAvailability.mockImplementation(() => availability(true))
		const wrapper = render()
		await flushPromises()
		for (const event of ["alert_created", "waiting_on_you", "case_closed", "report_ready"]) {
			expect(wrapper.find(`[data-testid=notification-pref-${event}]`).exists()).toBe(true)
		}
		expect(wrapper.find("[data-testid=notification-pref-alert_created-severity]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=notification-pref-case_closed-severity]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=notification-preferences-save]").attributes("disabled")).toBeDefined()
		expect(wrapper.find("[data-testid=notification-email-unavailable]").exists()).toBe(false)
		wrapper.unmount()
	})

	it("saves every event once a choice changed", async () => {
		api.getAvailability.mockImplementation(() => availability(true))
		const changed = DEFAULTS.map(pref => (pref.event === "case_closed" ? { ...pref, in_app: false } : pref))
		api.setPreferences.mockResolvedValue({ data: { preferences: changed } })
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=notification-pref-case_closed-in-app]").trigger("click")
		const save = wrapper.get("[data-testid=notification-preferences-save]")
		expect(save.attributes("disabled")).toBeUndefined()
		await save.trigger("click")
		await flushPromises()
		expect(api.setPreferences).toHaveBeenCalledWith(changed)
		expect(wrapper.get("[data-testid=notification-preferences-save]").attributes("disabled")).toBeDefined()
		wrapper.unmount()
	})

	it("offers no save after a failed load, so the defaults never overwrite the user's choices", async () => {
		api.getAvailability.mockImplementation(() => availability(true))
		api.getPreferences.mockRejectedValue(new Error("down"))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=notification-pref-case_closed-in-app]").trigger("click")
		expect(wrapper.get("[data-testid=notification-preferences-save]").attributes("disabled")).toBeDefined()
		wrapper.unmount()
	})

	it("says why email cannot be chosen, and does not offer it", async () => {
		api.getAvailability.mockImplementation(() => availability(false, "The user has no email address"))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=notification-email-unavailable]").text()).toContain("no email address")
		expect(wrapper.find("[data-testid=notification-pref-alert_created-email] .n-base-selection--disabled").exists()).toBe(
			true
		)
		wrapper.unmount()
	})
})
