import type { Announcement } from "@/types/announcements"
import { computed, ref } from "vue"
import Api from "@/api"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"

/**
 * SOCFortress announcements ("What's new" in the toolbar, and the sign-in modal).
 *
 * Module-level state so the toolbar entry and the modal share one request: asked once per
 * session (`GET /announcements`, which the backend answers from its own hourly cache), a failure
 * is an empty list and asked again on the next load. Only SOC roles ask; the route serves no one
 * else. Cleared on logout (`stores/auth.ts:setLogout`).
 *
 * Which items a user has seen lives in this browser's localStorage, per username
 * (`SEEN_KEY_PREFIX + username`), pruned to the ids the feed still carries. The modal shows the
 * unseen `popup` items at most once per browser session (`MODAL_SESSION_KEY`), and showing it
 * marks them seen, so it never nags.
 */
export const SEEN_KEY_PREFIX = "copilot.announcements.seen."
export const MODAL_SESSION_KEY = "copilot.announcements.modal-shown"
/** Keep at most this many seen ids, whatever the feed does. */
const MAX_SEEN_IDS = 500

const announcements = ref<Announcement[]>([])
const enabled = ref(false)
const loaded = ref(false)
const seenIds = ref<string[]>([])
let seenFor = ""
let inflight: Promise<void> | null = null
let generation = 0

function seenKey(username: string) {
	return `${SEEN_KEY_PREFIX}${username}`
}

function readSeen(username: string): string[] {
	try {
		const parsed: unknown = JSON.parse(localStorage.getItem(seenKey(username)) || "[]")
		return Array.isArray(parsed) ? parsed.filter((id): id is string => typeof id === "string") : []
	} catch {
		return []
	}
}

function writeSeen(username: string, ids: string[]) {
	try {
		localStorage.setItem(seenKey(username), JSON.stringify(ids.slice(-MAX_SEEN_IDS)))
	} catch {
		// Storage full or disabled: the dot simply comes back next session.
	}
}

function syncSeenOwner(username: string) {
	if (seenFor !== username) {
		seenFor = username
		seenIds.value = readSeen(username)
	}
}

function mayAsk(): boolean {
	const auth = useAuthStore()
	return !!auth.userName && auth.isRoleGranted([AuthUserRole.Admin, AuthUserRole.Analyst])
}

function load(): Promise<void> {
	if (inflight) return inflight
	if (!mayAsk()) return Promise.resolve()

	const username = useAuthStore().userName
	syncSeenOwner(username)
	const asked = ++generation

	inflight = Api.announcements
		.getAnnouncements()
		.then(res => {
			if (asked !== generation) return
			enabled.value = res.data?.enabled === true
			announcements.value = enabled.value ? (res.data?.announcements ?? []) : []
			loaded.value = true
			// Forget ids the feed no longer carries, so the list cannot grow for ever.
			const current = new Set(announcements.value.map(a => a.id))
			const kept = seenIds.value.filter(id => current.has(id))
			if (kept.length !== seenIds.value.length) {
				seenIds.value = kept
				writeSeen(username, kept)
			}
		})
		.catch(() => {
			// Silent: announcements are never worth an error toast.
			if (asked !== generation) return
			enabled.value = false
			announcements.value = []
		})
		.finally(() => {
			if (asked === generation) inflight = null
		})

	return inflight
}

function markSeen(ids: string[]) {
	const username = useAuthStore().userName
	if (!username || !ids.length) return
	syncSeenOwner(username)
	const merged = [...new Set([...seenIds.value, ...ids])]
	if (merged.length === seenIds.value.length) return
	seenIds.value = merged
	writeSeen(username, merged)
}

function modalAlreadyShown(): boolean {
	try {
		return sessionStorage.getItem(MODAL_SESSION_KEY) === "1"
	} catch {
		return false
	}
}

function rememberModalShown() {
	try {
		sessionStorage.setItem(MODAL_SESSION_KEY, "1")
	} catch {
		// Without sessionStorage the items are still marked seen, so it cannot repeat.
	}
}

/** Forget everything (logout, or a test). */
export function resetAnnouncements() {
	generation += 1
	inflight = null
	announcements.value = []
	enabled.value = false
	loaded.value = false
	seenIds.value = []
	seenFor = ""
	try {
		sessionStorage.removeItem(MODAL_SESSION_KEY)
	} catch {
		// nothing to clear
	}
}

export function useAnnouncements() {
	const seen = computed(() => new Set(seenIds.value))
	const unseen = computed(() => announcements.value.filter(a => !seen.value.has(a.id)))
	const popupQueue = computed(() => unseen.value.filter(a => a.popup))

	return {
		announcements,
		enabled,
		loaded,
		unseen,
		popupQueue,
		isSeen: (id: string) => seen.value.has(id),
		load,
		markSeen,
		modalAlreadyShown,
		rememberModalShown
	}
}
