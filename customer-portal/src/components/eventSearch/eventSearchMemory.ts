import type { EventSearchMemory, EventSearchState } from "@/types/siem"

/**
 * What event search remembers for a user, per customer (#1258): saved and recent searches
 * and the columns picked per source. It lives on the server, which owns the rules (names,
 * limits, de-duplication); `useEventSearchMemory` keeps the copy the page shows.
 */

export function emptyMemory(): EventSearchMemory {
	return { saved: [], recent: [], columns: {} }
}

const UNIT_WORDS: Record<EventSearchState["time_unit"], string> = { h: "hour", d: "day", w: "week" }

/** "last 24 hours", or the absolute range as given by `formatTime`. */
export function describeTime(state: EventSearchState, formatTime: (iso: string) => string): string {
	if (state.time_mode === "absolute" && state.time_from && state.time_to) {
		return `${formatTime(state.time_from)} → ${formatTime(state.time_to)}`
	}
	return `last ${state.time_amount} ${UNIT_WORDS[state.time_unit]}${state.time_amount === 1 ? "" : "s"}`
}
