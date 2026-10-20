import type { NotificationAvailability, PortalNotification } from "@/types/notifications"
import { readonly, ref } from "vue"
import Api from "@/api"

/**
 * The user's notifications kept by the server (#1282), when their customer has them on.
 *
 * Module state, one copy per page: the bell, the profile and the report poller read the
 * same answer. The availability is asked once and cached as the in-flight promise; the
 * feed's first page loads when the bell starts, and then only the unread count is polled
 * (every minute, never while the page is hidden), the page being re-read when the count
 * moves. `reset()` on logout: the next user is someone else.
 */

export const POLL_MS = 60_000
export const PAGE_SIZE = 20

const availability = ref<NotificationAvailability | null>(null)
const available = ref(false)
const items = ref<PortalNotification[]>([])
const unread = ref(0)
const hasMore = ref(false)
const loading = ref(false)

let availabilityRequest: Promise<NotificationAvailability | null> | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null
let pollers = 0
/** Bumped by reset(): an answer started before it is dropped, whatever it says. */
let generation = 0

function loadAvailability(): Promise<NotificationAvailability | null> {
	if (availabilityRequest) return availabilityRequest
	const started = generation
	availabilityRequest = (async () => {
		try {
			const data = (await Api.notifications.getAvailability()).data
			if (started !== generation) return null
			availability.value = data
			available.value = data.enabled === true
			return data
		} catch {
			// A failed lookup must not pin the bell to "off" for the session: retry next time.
			availabilityRequest = null
			return null
		}
	})()
	return availabilityRequest
}

async function refresh(): Promise<void> {
	if (!available.value) return
	const started = generation
	loading.value = true
	try {
		const data = (await Api.notifications.list(PAGE_SIZE)).data
		if (started !== generation) return
		items.value = data.notifications
		unread.value = data.unread_count
		hasMore.value = data.has_more
	} catch {
		// The bell keeps what it has; the next poll tries again.
	} finally {
		if (started === generation) loading.value = false
	}
}

async function loadMore(): Promise<void> {
	const oldest = items.value.at(-1)
	if (!available.value || !oldest || !hasMore.value) return
	const started = generation
	try {
		const data = (await Api.notifications.list(PAGE_SIZE, oldest.id)).data
		if (started !== generation) return
		const known = new Set(items.value.map(item => item.id))
		items.value = [...items.value, ...data.notifications.filter(item => !known.has(item.id))]
		unread.value = data.unread_count
		hasMore.value = data.has_more
	} catch {
		// Nothing lost: the button stays, and can be pressed again.
	}
}

async function poll(): Promise<void> {
	if (!available.value || document.visibilityState === "hidden") return
	const started = generation
	try {
		const count = (await Api.notifications.unreadCount()).data.unread_count
		if (started !== generation) return
		if (count !== unread.value) await refresh()
	} catch {
		// Polled again in a minute.
	}
}

async function markRead(ids: number[] | "all"): Promise<void> {
	if (!available.value) return
	const marking = ids === "all" ? null : new Set(ids)
	const marked = (item: PortalNotification) => marking === null || marking.has(item.id)
	// At once, so the badge follows the click; the server's count settles it.
	const newlyRead = items.value.filter(item => !item.read && marked(item)).length
	items.value = items.value.map(item => (marked(item) ? { ...item, read: true } : item))
	unread.value = ids === "all" ? 0 : Math.max(0, unread.value - newlyRead)
	try {
		unread.value = (await Api.notifications.markRead(ids)).data.unread_count
	} catch {
		await refresh()
	}
}

function onVisible() {
	if (document.visibilityState === "visible") void poll()
}

/** Start following the feed (the bell, while mounted). Calls nest: the last stop ends it. */
async function start(): Promise<void> {
	pollers += 1
	if (pollers > 1) return
	document.addEventListener("visibilitychange", onVisible)
	pollTimer = setInterval(() => void poll(), POLL_MS)
	await loadAvailability()
	await refresh()
}

function stop() {
	pollers = Math.max(0, pollers - 1)
	if (pollers > 0) return
	document.removeEventListener("visibilitychange", onVisible)
	if (pollTimer) clearInterval(pollTimer)
	pollTimer = null
}

function reset() {
	generation += 1
	availabilityRequest = null
	availability.value = null
	available.value = false
	items.value = []
	unread.value = 0
	hasMore.value = false
	loading.value = false
}

export function useServerNotifications() {
	return {
		/** Whether the server keeps this user's notifications: the bell shows them. */
		available: readonly(available),
		availability: readonly(availability),
		items: readonly(items),
		unread: readonly(unread),
		hasMore: readonly(hasMore),
		loading: readonly(loading),
		loadAvailability,
		refresh,
		loadMore,
		markRead,
		start,
		stop,
		reset
	}
}
