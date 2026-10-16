/**
 * The Talon action proposals the page's approval cards show (plan M5-11b), module-level and shared:
 *
 * - **One entry per proposal** (`entries`): the record CoPilot's `GET /api/talon/actions/{id}`
 *   last answered, the read's state and the decision in flight. Every card of one proposal (the
 *   chat's and the Approvals tab's) reads the same entry, so they update together, and a decision
 *   in flight disables the buttons of all of them: no second POST from a sibling card.
 * - **One poll for the page** (`tick`), not one per card. While a card is mounted and the page is
 *   visible, it reads CoPilot's mirror list (`GET /api/talon/actions?scope=mine`, and `pending` if a
 *   card isn't the user's own) once per tick, and reads a card's record (which syncs it from
 *   talon-analyst) only when its row changed, when it isn't in the list (every `SLOW_MS`), or to
 *   heal (every `HEAL_MS`). The tick starts at `FAST_MS`, backs off to `MAX_MS` while nothing
 *   changes, and returns to `FAST_MS` on any change, decision or return to the page. Nothing is
 *   read while the page is hidden. A record whose CoPilot state is settled but talon-analyst's
 *   isn't (`refused`, `unreported`) is read every `SLOW_MS`, so the thread heals.
 * - **The resume guard** (`claimResume`).
 *
 * All of it is cleared at logout (`resetTalonActions`, `stores/auth.ts:setLogout`).
 */
import type { TalonAction } from "@/types/talonActions"
import axios from "axios"
import { computed, getCurrentInstance, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import Api from "@/api"
import { refusalDetail } from "@/api/endpoints/talonV2"
import { TALON_V2_FAILED } from "@/api/talonV2Parser"
import { noteApprovalsChanged } from "@/composables/useTalonApprovals"
import { pollClass } from "./approvals"

/** The poll's first and fastest tick. */
export const TALON_CARDS_FAST_MS = 10_000
/** The slowest tick while nothing changes. */
export const TALON_CARDS_MAX_MS = 30_000
/** A card not in the list, or settled here but not at talon-analyst, is read at most this often. */
export const TALON_CARDS_SLOW_MS = 60_000
/** Every open card is read from talon-analyst at least this often, whatever the list says. */
export const TALON_CARDS_HEAL_MS = 300_000

/** Shown when a decision's answer never came: CoPilot may have decided it anyway. */
export const DECISION_LOST = "The answer was lost; checking what happened."

export type DecisionKind = "approve" | "deny" | "withdraw"

export interface CardEntry {
	action: TalonAction | null
	/** `Date.now()` when `action` was taken: `expires_in_seconds` counts from here. */
	receivedAt: number
	loading: boolean
	loadError: string | null
	/** CoPilot answered 404: the proposal is not this user's to see (any more). */
	gone: boolean
	busy: DecisionKind | null
	decisionError: string | null
	decisionNote: string | null
	/** A decision's answer was lost: cleared once a read shows what happened. */
	lost: boolean
}

interface Meta {
	/** Bumped by every record taken: a read started before is dropped. */
	version: number
	lastReadAt: number
	controller: AbortController | null
}

const entries = reactive(new Map<string, CardEntry>())
const meta = new Map<string, Meta>()
const mounted = new Map<string, number>()
const resumed = new Set<string>()
/** The poll's clock, for what depends on time (`blocksThread`'s result window). */
export const cardsClock = ref(Date.now())

let timer: ReturnType<typeof setTimeout> | null = null
let interval = TALON_CARDS_FAST_MS
let listening = false
let listController: AbortController | null = null
// Bumped by a reset: an answer for the previous user changes nothing.
let generation = 0

function visible() {
	return typeof document === "undefined" || document.visibilityState !== "hidden"
}

function entryOf(id: string): CardEntry {
	let entry = entries.get(id)
	if (!entry) {
		entries.set(id, {
			action: null,
			receivedAt: 0,
			loading: false,
			loadError: null,
			gone: false,
			busy: null,
			decisionError: null,
			decisionNote: null,
			lost: false
		})
		entry = entries.get(id) as CardEntry
	}
	return entry
}

function metaOf(id: string): Meta {
	let m = meta.get(id)
	if (!m) {
		m = { version: 0, lastReadAt: 0, controller: null }
		meta.set(id, m)
	}
	return m
}

function errorOf(err: unknown): { status: number | null; detail: string } {
	if (axios.isAxiosError(err)) {
		return { status: err.response?.status ?? null, detail: refusalDetail(err.response?.data) }
	}
	return { status: null, detail: TALON_V2_FAILED }
}

/** CoPilot's answer carries this proposal's record: anything else is no answer. */
function recordOf(data: unknown, id: string): TalonAction {
	const next = (data as { action?: unknown } | null)?.action as TalonAction | undefined
	if (!next || typeof next !== "object" || next.id !== id || typeof next.state !== "string") {
		throw new Error("not the proposal's record")
	}
	return next
}

/** What the poll compares a list row with: anything a card shows that can change. */
function signature(action: TalonAction): string {
	return JSON.stringify([
		action.state,
		action.talon_status,
		action.expired,
		action.outcome_reported,
		action.can_decide,
		action.decision ?? null,
		action.approver_username ?? null,
		action.state_reason ?? null,
		action.result_due_by ?? null
	])
}

/** Has the outcome of a lost decision become visible? */
function settledSinceLost(action: TalonAction): boolean {
	return !["pending", "claiming", "claimed", "executing"].includes(action.state)
}

function take(id: string, next: TalonAction) {
	const entry = entryOf(id)
	const before = entry.action
	metaOf(id).version += 1
	entry.action = next
	entry.receivedAt = Date.now()
	entry.gone = false
	entry.loadError = null
	if (entry.lost && settledSinceLost(next)) {
		entry.lost = false
		entry.decisionError = null
	}
	if (before && signature(before) !== signature(next)) {
		noteApprovalsChanged() // the Approvals badge follows
		if (interval !== TALON_CARDS_FAST_MS) {
			interval = TALON_CARDS_FAST_MS
			schedule()
		}
	}
}

/** Read one proposal from CoPilot (which syncs it from talon-analyst as the caller). */
export async function loadCard(id: string): Promise<void> {
	const entry = entryOf(id)
	const m = metaOf(id)
	m.controller?.abort()
	const own = new AbortController()
	m.controller = own
	m.lastReadAt = Date.now()
	const started = m.version
	const asked = generation
	entry.loading = true
	try {
		const res = await Api.talonActions.get(id, own.signal)
		if (own.signal.aborted || asked !== generation) return
		const next = recordOf(res.data, id)
		if (started === m.version) take(id, next)
	} catch (err) {
		if (own.signal.aborted || asked !== generation || axios.isCancel(err)) return
		const { status, detail } = errorOf(err)
		entry.loadError = detail
		if (status === 404) {
			// Not this user's to see or decide (any more): no old record, no buttons.
			entry.gone = true
			entry.action = null
		}
	} finally {
		if (m.controller === own) {
			m.controller = null
			if (asked === generation) entry.loading = false
		}
	}
}

/** Approve, deny or withdraw. One at a time per proposal, whichever card asks. */
export async function decideCard(id: string, kind: DecisionKind): Promise<void> {
	const entry = entryOf(id)
	if (entry.busy || !entry.action) return
	const m = metaOf(id)
	entry.busy = kind
	entry.decisionError = null
	entry.decisionNote = null
	entry.lost = false
	m.version += 1 // a read in flight is now stale
	m.controller?.abort()
	m.controller = null
	const asked = generation
	let reread = false
	try {
		const call =
			kind === "approve"
				? Api.talonActions.approve
				: kind === "deny"
					? Api.talonActions.deny
					: Api.talonActions.withdraw
		const res = await call(id)
		if (asked !== generation) return
		take(id, recordOf(res.data, id))
		// CoPilot answers 200 with `success: false` when it decided but the run didn't succeed.
		if (res.data.success === false && res.data.message) entry.decisionNote = res.data.message
	} catch (err) {
		if (asked !== generation) return
		const { status, detail } = errorOf(err)
		if (status === null || status >= 500) {
			// No answer, or not CoPilot's own refusal: it may have decided (and run) it anyway.
			entry.lost = true
			entry.decisionError = DECISION_LOST
		} else {
			entry.decisionError = detail
		}
		reread = true
	} finally {
		if (asked === generation) {
			entry.busy = null
			interval = TALON_CARDS_FAST_MS
			noteApprovalsChanged()
			if (reread) loadCard(id)
			schedule()
		}
	}
}

// ── the page's poll ──────────────────────────────────────────────────────────

function clearTimer() {
	if (timer) clearTimeout(timer)
	timer = null
}

/** The mounted proposals the poll still has to watch. */
function watched(): string[] {
	return [...mounted.keys()].filter(id => {
		const entry = entries.get(id)
		if (!entry || entry.gone) return false
		return !entry.action || pollClass(entry.action, Date.now()) !== "final"
	})
}

function schedule() {
	clearTimer()
	if (!visible() || !watched().length) return
	timer = setTimeout(() => {
		timer = null
		tick()
	}, interval)
}

/** Whether the poll reads this card's record now (see the module's comment). */
function shouldRead(
	action: TalonAction | null,
	row: TalonAction | undefined,
	moved: boolean,
	listed: boolean,
	since: number,
	now: number
): boolean {
	if (!action) return since >= TALON_CARDS_FAST_MS // a failed first read: try again
	if (pollClass(action, now) === "slow") return since >= TALON_CARDS_SLOW_MS
	if (moved) return true
	if (!row || !listed) return since >= TALON_CARDS_SLOW_MS
	return since >= TALON_CARDS_HEAL_MS
}

async function tick() {
	clearTimer()
	if (!visible()) return
	cardsClock.value = Date.now()
	const ids = watched()
	if (!ids.length) return
	const asked = generation
	const now = Date.now()
	let changed = false

	const scopes = new Set<"mine" | "pending">()
	for (const id of ids) {
		const action = entries.get(id)?.action
		if (action) scopes.add(action.is_requester ? "mine" : "pending")
	}
	const rows = new Map<string, TalonAction>()
	let listed = scopes.size > 0
	listController?.abort()
	const own = new AbortController()
	listController = own
	for (const scope of scopes) {
		try {
			const res = await Api.talonActions.list(scope, own.signal)
			for (const row of Array.isArray(res.data?.actions) ? res.data.actions : []) rows.set(row.id, row)
		} catch {
			listed = false
		}
		if (own.signal.aborted || asked !== generation) return
	}
	if (listController === own) listController = null

	for (const id of ids) {
		const entry = entries.get(id)
		if (!entry || entry.busy || entry.loading) continue
		const since = now - metaOf(id).lastReadAt
		const action = entry.action
		const row = rows.get(id)
		const moved = !!action && !!row && signature(row) !== signature(action)
		if (moved) changed = true
		if (shouldRead(action, row, moved, listed, since, now)) loadCard(id)
	}

	if (asked !== generation) return
	// Nothing changed since the last tick: back off.
	interval = changed ? TALON_CARDS_FAST_MS : Math.min(TALON_CARDS_MAX_MS, interval * 2)
	schedule()
}

function onVisibility() {
	if (visible()) {
		interval = TALON_CARDS_FAST_MS
		tick()
	} else {
		clearTimer()
		listController?.abort()
		listController = null
	}
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

/** A card of this proposal is shown: read it if it hasn't been, and keep it fresh. */
export function registerCard(id: string) {
	mounted.set(id, (mounted.get(id) ?? 0) + 1)
	listen()
	const entry = entryOf(id)
	if (!entry.action && !entry.loading && !entry.gone) loadCard(id)
	interval = TALON_CARDS_FAST_MS
	schedule()
}

/** A card of this proposal is gone. The record stays (the thread still derives from it). */
export function unregisterCard(id: string) {
	const left = (mounted.get(id) ?? 1) - 1
	if (left > 0) {
		mounted.set(id, left)
		return
	}
	mounted.delete(id)
	if (!mounted.size) {
		clearTimer()
		listController?.abort()
		listController = null
		unlisten()
	}
}

/** One card's view of its proposal: the shared entry, kept fresh while the card is mounted. */
export function useActionCard(id: string) {
	if (getCurrentInstance()) {
		onMounted(() => registerCard(id))
		onBeforeUnmount(() => unregisterCard(id))
	}
	return {
		entry: computed(() => entryOf(id)),
		decide: (kind: DecisionKind) => decideCard(id, kind)
	}
}

export function knownAction(id: string): CardEntry | undefined {
	return entries.get(id)
}

/**
 * The thread's resume for this set of proposals is to be sent now: true once per key for the whole
 * session, so re-renders, polls and remounts can't send it twice.
 */
export function claimResume(threadId: string, approvalIds: string[]): boolean {
	const key = `${threadId}:${[...approvalIds].sort().join(",")}`
	if (resumed.has(key)) return false
	resumed.add(key)
	return true
}

/** Forget every proposal, the poll and the resume guard (logout, or a test). */
export function resetTalonActions() {
	generation += 1
	clearTimer()
	listController?.abort()
	listController = null
	for (const m of meta.values()) m.controller?.abort()
	meta.clear()
	entries.clear()
	mounted.clear()
	resumed.clear()
	unlisten()
	interval = TALON_CARDS_FAST_MS
	cardsClock.value = Date.now()
}
