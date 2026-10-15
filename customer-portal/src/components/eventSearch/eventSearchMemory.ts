import type { DisplayColumn } from "@/types/siem"

/**
 * What event search remembers for a user (#1258), per customer: named saved queries,
 * the last queries run, and the columns picked per event source. Pure functions over a
 * plain object, so the rules (names, limits, de-duplication, tolerance to old or broken
 * data) are tested without a browser; `useEventSearchMemory` stores the object.
 */

export const SAVED_LIMIT = 50
export const RECENT_LIMIT = 10
const NAME_MAX = 80

export type TimeUnit = "h" | "d" | "w"

/** Everything that makes a search: run it again and the same events come back. */
export interface QueryState {
	sourceName: string
	query: string
	timeMode: "relative" | "absolute"
	/** Relative mode: e.g. 24 h. */
	time: number
	unit: TimeUnit
	/** Absolute mode: epoch milliseconds. */
	timeFrom: number | null
	timeTo: number | null
	pageSize: number
}

export interface SavedQuery extends QueryState {
	id: string
	name: string
	savedAt: number
}

export interface RecentQuery extends QueryState {
	ranAt: number
}

export interface EventSearchMemory {
	version: 1
	saved: SavedQuery[]
	recent: RecentQuery[]
	/** The user's own columns per event source; absent means the SOC's (or the default) layout. */
	columns: Record<string, DisplayColumn[]>
}

export function emptyMemory(): EventSearchMemory {
	return { version: 1, saved: [], recent: [], columns: {} }
}

/** The storage key: one entry per user and customer, so two users of one browser never mix. */
export function memoryKey(username: string, customerCode: string): string {
	return `event-search:${username}:${customerCode}`
}

const UNITS: TimeUnit[] = ["h", "d", "w"]

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value)
}

function readState(raw: Record<string, unknown>): QueryState | null {
	if (typeof raw.sourceName !== "string" || !raw.sourceName) return null
	const timeMode = raw.timeMode === "absolute" ? "absolute" : "relative"
	const timeFrom = typeof raw.timeFrom === "number" ? raw.timeFrom : null
	const timeTo = typeof raw.timeTo === "number" ? raw.timeTo : null
	if (timeMode === "absolute" && (timeFrom === null || timeTo === null)) return null
	return {
		sourceName: raw.sourceName,
		query: typeof raw.query === "string" ? raw.query : "",
		timeMode,
		time: typeof raw.time === "number" && raw.time > 0 ? raw.time : 24,
		unit: UNITS.includes(raw.unit as TimeUnit) ? (raw.unit as TimeUnit) : "h",
		timeFrom,
		timeTo,
		pageSize: typeof raw.pageSize === "number" && raw.pageSize > 0 ? raw.pageSize : 50
	}
}

/**
 * Reads whatever was stored, keeping every entry that still makes sense: data written by an
 *  older build, edited by hand or cut short never breaks the page.
 */
export function normalizeMemory(raw: unknown): EventSearchMemory {
	let value = raw
	if (typeof value === "string") {
		try {
			value = JSON.parse(value)
		} catch {
			return emptyMemory()
		}
	}
	if (!isRecord(value)) return emptyMemory()

	const saved: SavedQuery[] = []
	for (const entry of Array.isArray(value.saved) ? value.saved : []) {
		if (!isRecord(entry) || typeof entry.name !== "string" || !entry.name.trim()) continue
		const state = readState(entry)
		if (!state) continue
		saved.push({
			...state,
			id: typeof entry.id === "string" && entry.id ? entry.id : `saved-${saved.length}`,
			name: entry.name.trim().slice(0, NAME_MAX),
			savedAt: typeof entry.savedAt === "number" ? entry.savedAt : 0
		})
	}

	const recent: RecentQuery[] = []
	for (const entry of Array.isArray(value.recent) ? value.recent : []) {
		if (!isRecord(entry)) continue
		const state = readState(entry)
		if (state) recent.push({ ...state, ranAt: typeof entry.ranAt === "number" ? entry.ranAt : 0 })
	}

	const columns: Record<string, DisplayColumn[]> = {}
	for (const [source, list] of Object.entries(isRecord(value.columns) ? value.columns : {})) {
		if (!Array.isArray(list)) continue
		const kept = list
			.filter((c): c is Record<string, unknown> => isRecord(c) && typeof c.key === "string" && !!c.key)
			.map(c => ({ key: c.key as string, label: typeof c.label === "string" && c.label ? c.label : (c.key as string) }))
		if (kept.length) columns[source] = kept
	}

	return {
		version: 1,
		saved: saved.slice(0, SAVED_LIMIT),
		recent: recent.slice(0, RECENT_LIMIT),
		columns
	}
}

function pickState(state: QueryState): QueryState {
	const { sourceName, query, timeMode, time, unit, timeFrom, timeTo, pageSize } = state
	return {
		sourceName,
		query: query.trim(),
		timeMode,
		time,
		unit,
		timeFrom: timeMode === "absolute" ? timeFrom : null,
		timeTo: timeMode === "absolute" ? timeTo : null,
		pageSize
	}
}

/** Two searches are the same when they ask the same events, whatever the page size. */
export function sameQuery(a: QueryState, b: QueryState): boolean {
	const x = pickState(a)
	const y = pickState(b)
	if (x.sourceName !== y.sourceName || x.query !== y.query || x.timeMode !== y.timeMode) return false
	return x.timeMode === "relative"
		? x.time === y.time && x.unit === y.unit
		: x.timeFrom === y.timeFrom && x.timeTo === y.timeTo
}

/**
 * Saves the search under a name. A name already used (whatever its case) is updated in
 * place rather than duplicated; newest first, at most `SAVED_LIMIT`.
 */
export function saveQuery(
	memory: EventSearchMemory,
	name: string,
	state: QueryState,
	now: number,
	makeId: () => string = () => `${now.toString(36)}-${Math.random().toString(36).slice(2, 8)}`
): { memory: EventSearchMemory; replaced: boolean } {
	const clean = name.trim().slice(0, NAME_MAX)
	if (!clean) throw new Error("A saved query needs a name")
	const existing = memory.saved.find(s => s.name.toLowerCase() === clean.toLowerCase())
	const entry: SavedQuery = { ...pickState(state), id: existing?.id ?? makeId(), name: clean, savedAt: now }
	const others = memory.saved.filter(s => s !== existing)
	return { memory: { ...memory, saved: [entry, ...others].slice(0, SAVED_LIMIT) }, replaced: !!existing }
}

export function deleteQuery(memory: EventSearchMemory, id: string): EventSearchMemory {
	return { ...memory, saved: memory.saved.filter(s => s.id !== id) }
}

/** Records a search just run: on top, once, at most `RECENT_LIMIT`. */
export function rememberRecent(memory: EventSearchMemory, state: QueryState, now: number): EventSearchMemory {
	const entry: RecentQuery = { ...pickState(state), ranAt: now }
	const others = memory.recent.filter(r => !sameQuery(r, entry))
	return { ...memory, recent: [entry, ...others].slice(0, RECENT_LIMIT) }
}

export function clearRecent(memory: EventSearchMemory): EventSearchMemory {
	return { ...memory, recent: [] }
}

/** The user's columns for a source; `null` (or an empty list) goes back to the source's layout. */
export function setColumns(memory: EventSearchMemory, sourceName: string, columns: DisplayColumn[] | null): EventSearchMemory {
	const next = { ...memory.columns }
	if (columns?.length) next[sourceName] = columns.map(c => ({ key: c.key, label: c.label.trim() || c.key }))
	else delete next[sourceName]
	return { ...memory, columns: next }
}

/** "last 24 hours", or the absolute range as given by `formatTime`. */
export function describeTime(state: QueryState, formatTime: (epoch: number) => string): string {
	if (state.timeMode === "absolute" && state.timeFrom !== null && state.timeTo !== null) {
		return `${formatTime(state.timeFrom)} → ${formatTime(state.timeTo)}`
	}
	const words: Record<TimeUnit, string> = { h: "hour", d: "day", w: "week" }
	return `last ${state.time} ${words[state.unit]}${state.time === 1 ? "" : "s"}`
}
