// The run view's layout, as a plain function (TalonRunTimeline.vue renders it): a lane per trace,
// spans nested by `parent_id` (depth-first, siblings by start time), and each bar placed by its start
// and sized by its length on one shared time axis. Only the DTO's own fields are read
// (`schema/talon_runs.py`); a span is never looked into beyond them.
import type { TalonTimelineSpan } from "@/types/talonUsage"

/** The narrowest bar, in percent of the axis, so an instant span is still seen. */
export const TIMELINE_MIN_WIDTH_PCT = 0.5
/** The deepest indent drawn (deeper spans keep their depth, drawn at this one), so a deep tree stays readable. */
export const TIMELINE_MAX_INDENT = 12

export interface TimelineRow {
	span: TalonTimelineSpan
	depth: number
	leftPct: number
	widthPct: number
}

export interface TimelineLane {
	traceId: string
	/** "Trace 1", with the stage its spans carry (`S5`) when one does. */
	label: string
	stage: string | null
	rows: TimelineRow[]
}

export interface TimelineLayout {
	lanes: TimelineLane[]
	/** Spans whose start or end time doesn't parse: not placed, counted for the `dropped` note. */
	unreadable: number
	/** The axis: the earliest start and the latest end, in milliseconds since the epoch. */
	startMs: number
	endMs: number
}

/** An ISO time as milliseconds; the DTO's microseconds are cut to what `Date` reads. */
export function timeMs(iso: string): number {
	const trimmed = iso.replace(/(\.\d{3})\d+/, "$1")
	const ms = Date.parse(trimmed)
	return Number.isFinite(ms) ? ms : Number.NaN
}

function round(value: number): number {
	return Math.round(value * 1000) / 1000
}

function byStart(a: TalonTimelineSpan, b: TalonTimelineSpan): number {
	const d = timeMs(a.start_time) - timeMs(b.start_time)
	if (d !== 0 && Number.isFinite(d)) return d
	return a.span_id < b.span_id ? -1 : a.span_id > b.span_id ? 1 : 0
}

export function layoutTimeline(spans: TalonTimelineSpan[]): TimelineLayout {
	const usable = spans.filter(s => Number.isFinite(timeMs(s.start_time)) && Number.isFinite(timeMs(s.end_time)))
	const unreadable = spans.length - usable.length
	if (!usable.length) return { lanes: [], unreadable, startMs: 0, endMs: 0 }
	const startMs = Math.min(...usable.map(s => timeMs(s.start_time)))
	const endMs = Math.max(...usable.map(s => Math.max(timeMs(s.end_time), timeMs(s.start_time))))
	const total = Math.max(endMs - startMs, 1)

	const traces = new Map<string, TalonTimelineSpan[]>()
	for (const span of usable) {
		const list = traces.get(span.trace_id) ?? []
		list.push(span)
		traces.set(span.trace_id, list)
	}

	const lanes = [...traces.entries()]
		.map(([traceId, list]) => ({ traceId, list: [...list].sort(byStart) }))
		.sort((a, b) => byStart(a.list[0], b.list[0]))
		.map(({ traceId, list }, index) => {
			const ids = new Set(list.map(s => s.span_id))
			const children = new Map<string, TalonTimelineSpan[]>()
			const roots: TalonTimelineSpan[] = []
			for (const span of list) {
				// A parent outside this trace's spans (not read, or another trace) makes it a root here.
				if (span.parent_id && span.parent_id !== span.span_id && ids.has(span.parent_id)) {
					const siblings = children.get(span.parent_id) ?? []
					siblings.push(span)
					children.set(span.parent_id, siblings)
				} else {
					roots.push(span)
				}
			}
			const rows: TimelineRow[] = []
			const placed = new Set<string>()
			const visit = (span: TalonTimelineSpan, depth: number) => {
				if (placed.has(span.span_id)) return
				placed.add(span.span_id)
				const start = timeMs(span.start_time)
				// A span that ends before it starts is taken as an instant.
				const duration = Math.max(timeMs(span.end_time) - start, 0)
				// Never so far right that the narrowest bar has no room: an instant at the axis end is still seen.
				const leftPct = round(Math.min(((start - startMs) / total) * 100, 100 - TIMELINE_MIN_WIDTH_PCT))
				const widthPct = round(
					Math.min(Math.max((duration / total) * 100, TIMELINE_MIN_WIDTH_PCT), 100 - leftPct)
				)
				rows.push({ span, depth, leftPct, widthPct })
				for (const child of children.get(span.span_id) ?? []) visit(child, depth + 1)
			}
			roots.forEach(root => visit(root, 0))
			// Spans only reachable through a cycle of parents: shown at the top level, never lost.
			list.forEach(span => visit(span, 0))
			const stage = list.find(s => s.stage)?.stage ?? null
			return {
				traceId,
				label: stage ? `Trace ${index + 1} · ${stage}` : `Trace ${index + 1}`,
				stage,
				rows
			}
		})

	return { lanes, unreadable, startMs, endMs }
}

/** What a span ran: its model or its tool, when the DTO names one. */
export function spanSubject(span: Pick<TalonTimelineSpan, "model" | "tool">): string | null {
	return span.tool ?? span.model ?? null
}

/** Its token counts for reading (`1,200 in · 300 out`), or null when it has none. */
export function spanTokens(
	span: Pick<TalonTimelineSpan, "prompt_tokens" | "completion_tokens" | "total_tokens">,
	format: (n: number) => string
): string | null {
	const parts: string[] = []
	if (span.prompt_tokens !== null) parts.push(`${format(span.prompt_tokens)} in`)
	if (span.completion_tokens !== null) parts.push(`${format(span.completion_tokens)} out`)
	if (!parts.length && span.total_tokens !== null) parts.push(`${format(span.total_tokens)} tokens`)
	return parts.length ? parts.join(" · ") : null
}
