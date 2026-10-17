import type { TalonAction } from "@/types/talonActions"
import axios from "axios"
import { computed, getCurrentInstance, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import { refusalDetail } from "@/api/endpoints/talonV2"
import { TALON_V2_FAILED } from "@/api/talonV2Parser"

/**
 * The Talon v2 action proposals waiting in CoPilot (plan M5-11b, decision b): `GET
 * /api/talon/actions?scope=pending`, the proposals the user may decide now plus their own pending
 * ones, for the AI Analyst page's Approvals tab and its count badge.
 *
 * Module-level, like `useTalonV2Availability`: every caller shares one list and one poll. A caller
 * that wants it kept fresh calls `watchApprovals()` from a component: while at least one such
 * component is mounted and the page is visible, the list is read every `TALON_APPROVALS_POLL_MS`,
 * and again as soon as the page becomes visible. Nothing is read while the page is hidden or after
 * the last watcher unmounts. Cleared on logout (`stores/auth.ts:setLogout`), which also stops the
 * poll; the next user starts with nothing.
 *
 * The badge counts the proposals this user may decide now (`can_decide`): their own pending ones
 * that they can't decide (an analyst's quarantine) are listed, not counted.
 */

/** How often the pending list is read while the page is visible. */
export const TALON_APPROVALS_POLL_MS = 30_000

const actions = ref<TalonAction[]>([])
const loaded = ref(false)
const error = ref<string | null>(null)
let watchers = 0
let timer: ReturnType<typeof setTimeout> | null = null
let controller: AbortController | null = null
let listening = false
// Bumped by a reset: an answer for the previous user changes nothing.
let generation = 0

function visible() {
	return typeof document === "undefined" || document.visibilityState !== "hidden"
}

function clearTimer() {
	if (timer) clearTimeout(timer)
	timer = null
}

function schedule() {
	clearTimer()
	if (watchers > 0 && visible()) timer = setTimeout(refreshApprovals, TALON_APPROVALS_POLL_MS)
}

/** Read the pending list now (a decision was made, or the poll is due). */
export async function refreshApprovals(): Promise<void> {
	clearTimer()
	controller?.abort()
	const own = new AbortController()
	controller = own
	const asked = generation
	try {
		const res = await Api.talonActions.list("pending", own.signal)
		if (asked !== generation || own.signal.aborted) return
		actions.value = Array.isArray(res.data?.actions) ? res.data.actions : []
		loaded.value = true
		error.value = null
	} catch (err) {
		if (asked !== generation || own.signal.aborted || axios.isCancel(err)) return
		error.value = axios.isAxiosError(err) ? refusalDetail(err.response?.data) : TALON_V2_FAILED
	} finally {
		if (controller === own) {
			controller = null
			if (asked === generation) schedule()
		}
	}
}

function onVisibility() {
	if (watchers === 0) return
	if (visible()) {
		refreshApprovals()
		return
	}
	clearTimer()
	controller?.abort()
	controller = null
}

function listen() {
	if (listening || typeof document === "undefined") return
	document.addEventListener("visibilitychange", onVisibility)
	listening = true
}

function unlisten() {
	if (!listening) return
	document.removeEventListener("visibilitychange", onVisibility)
	listening = false
}

/** A proposal changed somewhere (a card decided it, or saw it move): read the list again if it is shown. */
export function noteApprovalsChanged() {
	if (watchers > 0) refreshApprovals()
}

/** Forget the list and stop the poll (logout, or a test). */
export function resetTalonApprovals() {
	generation += 1
	clearTimer()
	controller?.abort()
	controller = null
	watchers = 0
	unlisten()
	actions.value = []
	loaded.value = false
	error.value = null
}

/**
 * Keep the list fresh while the calling component is mounted (and the page visible). Called from
 * a component's setup, it stops on unmount; the returned function stops it earlier.
 */
export function watchApprovals() {
	watchers += 1
	const asked = generation
	listen()
	if (visible()) refreshApprovals()
	let stopped = false
	const stop = () => {
		if (stopped) return
		stopped = true
		// A reset (logout) already dropped every watcher.
		if (asked !== generation) return
		watchers = Math.max(0, watchers - 1)
		if (watchers === 0) {
			clearTimer()
			controller?.abort()
			controller = null
			unlisten()
		}
	}
	if (getCurrentInstance()) onBeforeUnmount(stop)
	return stop
}

export function useTalonApprovals() {
	return {
		actions: computed(() => actions.value),
		count: computed(() => actions.value.filter(a => a.can_decide).length),
		loaded: computed(() => loaded.value),
		error: computed(() => error.value),
		refresh: refreshApprovals
	}
}
