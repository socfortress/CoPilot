import type { DisplayColumn, EventSearchMemory, EventSearchState } from "@/types/siem"

/**
 * What event search remembers for a user, per customer (#1258): saved and recent searches,
 * the columns picked per source and the column templates to switch between. It lives on the server, which owns the rules (names,
 * limits, de-duplication); `useEventSearchMemory` keeps the copy the page shows.
 */

export function emptyMemory(): EventSearchMemory {
	return { saved: [], recent: [], columns: {}, templates: [] }
}

const UNIT_WORDS: Record<EventSearchState["time_unit"], string> = { h: "hour", d: "day", w: "week" }

/** "last 24 hours", or the absolute range as given by `formatTime`. */
export function describeTime(state: EventSearchState, formatTime: (iso: string) => string): string {
	if (state.time_mode === "absolute" && state.time_from && state.time_to) {
		return `${formatTime(state.time_from)} → ${formatTime(state.time_to)}`
	}
	return `last ${state.time_amount} ${UNIT_WORDS[state.time_unit]}${state.time_amount === 1 ? "" : "s"}`
}

/** Whether two column lists show the same thing: the same fields, in order, under the same headers. */
export function sameColumns(a: DisplayColumn[] | null | undefined, b: DisplayColumn[] | null | undefined): boolean {
	if (!a?.length || !b?.length) return !a?.length && !b?.length
	return a.length === b.length && a.every((column, i) => column.key === b[i]!.key && column.label === b[i]!.label)
}
