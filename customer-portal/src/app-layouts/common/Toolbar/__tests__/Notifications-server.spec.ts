import type { PortalNotification } from "@/types/notifications"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { nextTick } from "vue"
import NotificationsList from "@/components/common/Notifications/List.vue"
import NotificationsToolbar from "@/components/common/Notifications/Toolbar.vue"
import { useBell } from "@/composables/common/useBell"
import { useNotifications } from "@/composables/common/useNotifications"
import { useServerNotifications } from "@/composables/common/useServerNotifications"

const api = vi.hoisted(() => ({
	getAvailability: vi.fn(),
	list: vi.fn(),
	unreadCount: vi.fn(),
	markRead: vi.fn()
}))
vi.mock("@/api", () => ({ default: { notifications: api } }))
vi.mock("@/router", () => ({ default: { push: vi.fn(() => Promise.resolve()) } }))

function item(id: number, read = false): PortalNotification {
	return {
		id,
		customer_code: "ACME",
		event: "waiting_on_you",
		entity_type: "alert",
		entity_id: 40 + id,
		title: `The SOC is waiting on your reply: ${id}`,
		body: "Reply in its comments.",
		severity: "High",
		created_at: "2026-10-01T08:15:00",
		read
	}
}

async function serverOn(items: PortalNotification[], unread: number) {
	api.getAvailability.mockResolvedValue({
		data: { enabled: true, email_available: true, email_unavailable_reason: null, digest_hour_utc: 7 }
	})
	api.list.mockResolvedValue({ data: { notifications: items, unread_count: unread, has_more: false } })
	await useServerNotifications().start()
}

beforeEach(() => {
	setActivePinia(createPinia())
	Object.values(api).forEach(fn => fn.mockReset())
	useServerNotifications().stop()
	useServerNotifications().reset()
	useNotifications().list.value = [
		{ id: "report-1", category: "report", type: "success", title: "Report ready", description: "", read: false, date: new Date() }
	]
})

/** The bell with server notifications on (#1282). */
describe("the bell's server notifications", () => {
	it("shows the server's items, not the session list, and offers no Clear or Delete", async () => {
		await serverOn([item(2), item(1, true)], 1)
		const list = mount(NotificationsList)
		const toolbar = mount(NotificationsToolbar)
		await nextTick()
		const titles = list.findAll("[data-testid=notification-item] .title").map(t => t.text())
		expect(titles).toEqual(["The SOC is waiting on your reply: 2", "The SOC is waiting on your reply: 1"])
		expect(list.find(".delete-btn").exists()).toBe(false)
		expect(toolbar.text()).not.toContain("Clear")
		expect(useBell().hasUnread.value).toBe(true)
	})

	it("marks all read on the server", async () => {
		await serverOn([item(2), item(1)], 2)
		api.markRead.mockResolvedValue({ data: { marked: 2, unread_count: 0 } })
		const toolbar = mount(NotificationsToolbar)
		await toolbar.get("[data-testid=notifications-mark-all-read]").trigger("click")
		await flushPromises()
		expect(api.markRead).toHaveBeenCalledWith("all")
		expect(useBell().hasUnread.value).toBe(false)
	})

	it("marks one read when it is opened", async () => {
		await serverOn([item(2)], 1)
		api.markRead.mockResolvedValue({ data: { marked: 1, unread_count: 0 } })
		const list = mount(NotificationsList)
		await nextTick()
		await list.get("[data-testid=notification-item]").trigger("click")
		await flushPromises()
		expect(api.markRead).toHaveBeenCalledWith([2])
	})

	it("keeps the session list when notifications are off", async () => {
		api.getAvailability.mockResolvedValue({
			data: { enabled: false, email_available: true, email_unavailable_reason: null, digest_hour_utc: 7 }
		})
		await useServerNotifications().start()
		const list = mount(NotificationsList)
		await nextTick()
		expect(list.findAll("[data-testid=notification-item] .title").map(t => t.text())).toEqual(["Report ready"])
		expect(list.find(".delete-btn").exists()).toBe(true)
		expect(api.list).not.toHaveBeenCalled()
	})
})
