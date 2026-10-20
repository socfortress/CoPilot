import type { PortalNotification } from "@/types/notifications"
import { flushPromises } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { POLL_MS, useServerNotifications } from "../useServerNotifications"

const api = vi.hoisted(() => ({
	getAvailability: vi.fn(),
	list: vi.fn(),
	unreadCount: vi.fn(),
	markRead: vi.fn()
}))
vi.mock("@/api", () => ({ default: { notifications: api } }))

function item(id: number, read = false): PortalNotification {
	return {
		id,
		customer_code: "ACME",
		event: "case_closed",
		entity_type: "case",
		entity_id: id,
		title: `Case closed: ${id}`,
		body: null,
		severity: null,
		created_at: "2026-10-01T08:15:00",
		read
	}
}

function availability(enabled: boolean) {
	return Promise.resolve({
		data: { enabled, email_available: true, email_unavailable_reason: null, digest_hour_utc: 7 }
	})
}

function page(items: PortalNotification[], unread: number, hasMore = false) {
	return Promise.resolve({ data: { notifications: items, unread_count: unread, has_more: hasMore } })
}

/** The bell's server feed (#1282). */
describe("useServerNotifications", () => {
	const server = useServerNotifications()

	beforeEach(() => {
		vi.useFakeTimers()
		Object.values(api).forEach(fn => fn.mockReset())
		server.reset()
	})
	afterEach(() => {
		server.stop()
		server.reset()
		vi.useRealTimers()
	})

	it("asks once whether notifications are on, and shares the answer", async () => {
		api.getAvailability.mockImplementation(() => availability(true))
		await Promise.all([server.loadAvailability(), server.loadAvailability()])
		expect(api.getAvailability).toHaveBeenCalledTimes(1)
		expect(server.available.value).toBe(true)
	})

	it("asks again after a failed lookup, instead of staying off", async () => {
		api.getAvailability.mockRejectedValueOnce(new Error("down")).mockImplementation(() => availability(true))
		expect(await server.loadAvailability()).toBeNull()
		expect(server.available.value).toBe(false)
		await server.loadAvailability()
		expect(server.available.value).toBe(true)
	})

	it("reads nothing while notifications are off", async () => {
		api.getAvailability.mockImplementation(() => availability(false))
		await server.start()
		expect(api.list).not.toHaveBeenCalled()
		await vi.advanceTimersByTimeAsync(POLL_MS)
		expect(api.unreadCount).not.toHaveBeenCalled()
	})

	it("loads the first page, then polls only the count, and re-reads when it moves", async () => {
		api.getAvailability.mockImplementation(() => availability(true))
		api.list.mockImplementation(() => page([item(2), item(1, true)], 1))
		api.unreadCount.mockImplementation(() => Promise.resolve({ data: { unread_count: 1 } }))
		await server.start()
		expect(server.items.value.map(i => i.id)).toEqual([2, 1])
		expect(server.unread.value).toBe(1)

		await vi.advanceTimersByTimeAsync(POLL_MS)
		await flushPromises()
		expect(api.unreadCount).toHaveBeenCalledTimes(1)
		expect(api.list).toHaveBeenCalledTimes(1)

		api.unreadCount.mockImplementation(() => Promise.resolve({ data: { unread_count: 2 } }))
		api.list.mockImplementation(() => page([item(3), item(2), item(1, true)], 2))
		await vi.advanceTimersByTimeAsync(POLL_MS)
		await flushPromises()
		expect(server.items.value.map(i => i.id)).toEqual([3, 2, 1])
	})

	it("does not poll while the page is hidden", async () => {
		api.getAvailability.mockImplementation(() => availability(true))
		api.list.mockImplementation(() => page([], 0))
		await server.start()
		const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden")
		await vi.advanceTimersByTimeAsync(POLL_MS * 3)
		expect(api.unreadCount).not.toHaveBeenCalled()
		visibility.mockRestore()
	})

	it("marks read at once, and takes the server's count", async () => {
		api.getAvailability.mockImplementation(() => availability(true))
		api.list.mockImplementation(() => page([item(3), item(2), item(1)], 3))
		await server.start()
		let settle: (value: unknown) => void = () => {}
		api.markRead.mockImplementation(() => new Promise(resolve => (settle = resolve)))
		const marking = server.markRead([2])
		expect(server.items.value.find(i => i.id === 2)?.read).toBe(true)
		expect(server.unread.value).toBe(2)
		settle({ data: { marked: 1, unread_count: 5 } })
		await marking
		expect(api.markRead).toHaveBeenCalledWith([2])
		expect(server.unread.value).toBe(5)

		api.markRead.mockImplementation(() => Promise.resolve({ data: { marked: 2, unread_count: 0 } }))
		await server.markRead("all")
		expect(server.items.value.every(i => i.read)).toBe(true)
		expect(server.unread.value).toBe(0)
	})

	it("loads older pages without repeating an item", async () => {
		api.getAvailability.mockImplementation(() => availability(true))
		api.list.mockImplementationOnce(() => page([item(5), item(4)], 0, true))
		await server.start()
		api.list.mockImplementationOnce(() => page([item(4), item(3)], 0, false))
		await server.loadMore()
		expect(api.list).toHaveBeenLastCalledWith(20, 4)
		expect(server.items.value.map(i => i.id)).toEqual([5, 4, 3])
		expect(server.hasMore.value).toBe(false)
	})

	it("forgets everything at logout, and drops an answer that lands after it", async () => {
		api.getAvailability.mockImplementation(() => availability(true))
		let settle: (value: unknown) => void = () => {}
		api.list.mockImplementation(() => new Promise(resolve => (settle = resolve)))
		const starting = server.start()
		await flushPromises()
		server.reset()
		settle({ data: { notifications: [item(9)], unread_count: 1, has_more: false } })
		await starting
		expect(server.available.value).toBe(false)
		expect(server.items.value).toEqual([])
		expect(server.unread.value).toBe(0)
	})
})
