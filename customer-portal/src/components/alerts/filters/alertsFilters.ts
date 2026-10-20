import type { LocationQuery, LocationQueryRaw, LocationQueryValue } from "vue-router"
import type { AlertStatus } from "@/types/alerts"
import { WORKFLOW_STATUS_LABELS } from "@/utils/workflowStatus"

/**
 * The alerts list's filters (#1245), and the one place that maps them to and from the
 * URL and the API. The query string is their only store: a link, a reload or the back
 * button gives the same list.
 *
 * In the URL: `?title=…&status=OPEN&source=…&asset=…&tag=a&tag=b&from=YYYY-MM-DD&to=YYYY-MM-DD`.
 * Dates are calendar days in the browser's timezone — what the user picked, whatever
 * timezone they share the link to; the API gets the matching UTC instants.
 *
 * Two more arrive only from the Activity page's links (#1284), and are shown as chips
 * the user can remove but not add: `?detection=` (an exact alert name, where the title
 * searches) and `?opened_from=…&opened_before=…` (ISO 8601 instants: when the alerts
 * reached the SOC, the window the page counted in), so a click lists exactly its count.
 */
export interface AlertsFilters {
	title: string | null
	status: AlertStatus | null
	source: string | null
	asset: string | null
	/** An alert matches when it carries any of them. */
	tags: string[]
	from: string | null
	to: string | null
	/** An exact alert name: what the Activity page's detection links ask for. */
	detection: string | null
	/** When the alerts reached the SOC, as ISO 8601 instants: from (inclusive), before (exclusive). */
	openedFrom: string | null
	openedBefore: string | null
}

/** The filters the "Add filter" menu offers; the title search is always shown. */
export type AlertsMenuFilterType = "status" | "source" | "asset" | "tag" | "date"
/** Filters only a link sets (the Activity page's): shown as removable chips, never offered. */
export type AlertsLinkFilterType = "detection" | "opened"
export type AlertsFilterType = AlertsMenuFilterType | AlertsLinkFilterType

export const ALERTS_FILTER_TYPES: AlertsMenuFilterType[] = ["status", "source", "asset", "tag", "date"]
export const ALERTS_LINK_FILTER_TYPES: AlertsLinkFilterType[] = ["detection", "opened"]

export const ALERTS_FILTER_LABELS: Record<AlertsFilterType, string> = {
	status: "Status",
	source: "Source",
	asset: "Asset",
	tag: "Tag",
	date: "Created",
	detection: "Detection",
	opened: "Reached the SOC"
}

const QUERY_KEYS = [
	"title",
	"status",
	"source",
	"asset",
	"tag",
	"from",
	"to",
	"detection",
	"opened_from",
	"opened_before"
] as const

export const EMPTY_ALERTS_FILTERS: AlertsFilters = Object.freeze({
	title: null,
	status: null,
	source: null,
	asset: null,
	tags: [],
	from: null,
	to: null,
	detection: null,
	openedFrom: null,
	openedBefore: null
}) as AlertsFilters

type QueryValue = LocationQueryValue | LocationQueryValue[] | undefined

function values(value: QueryValue): string[] {
	const list = Array.isArray(value) ? value : [value]
	return list.map(item => (typeof item === "string" ? item.trim() : "")).filter(Boolean)
}

function single(value: QueryValue): string | null {
	return values(value)[0] ?? null
}

/** A `YYYY-MM-DD` that names a real day (no 2026-02-30). */
export function isDay(value: string | null): value is string {
	if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
	const [year, month, day] = value.split("-").map(Number)
	const date = new Date(year, month - 1, day)
	return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day
}

function isStatus(value: string | null): value is AlertStatus {
	return !!value && Object.hasOwn(WORKFLOW_STATUS_LABELS, value)
}

/** An ISO 8601 instant with a date and a time (`2026-10-01T12:00:00Z`), or null. */
export function instant(value: string | null): string | null {
	if (!value || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) return null
	return Number.isNaN(Date.parse(value)) ? null : value
}

/** The filters a query asks for. Anything unreadable is ignored rather than sent. */
export function filtersFromQuery(query: LocationQuery): AlertsFilters {
	const status = single(query.status)
	let from = single(query.from)
	let to = single(query.to)
	from = isDay(from) ? from : null
	to = isDay(to) ? to : null
	// A hand-edited link with the days the wrong way round still means that range.
	if (from && to && from > to) [from, to] = [to, from]

	let openedFrom = instant(single(query.opened_from))
	let openedBefore = instant(single(query.opened_before))
	// An empty or reversed window would be refused: drop it rather than send it.
	if (openedFrom && openedBefore && Date.parse(openedFrom) >= Date.parse(openedBefore)) {
		openedFrom = null
		openedBefore = null
	}

	return {
		title: single(query.title),
		status: isStatus(status) ? status : null,
		source: single(query.source),
		asset: single(query.asset),
		tags: [...new Set(values(query.tag))],
		from,
		to,
		detection: single(query.detection),
		openedFrom,
		openedBefore
	}
}

/** The query keys for `filters`; unset filters leave no key behind. */
export function filtersToQuery(filters: AlertsFilters): LocationQueryRaw {
	const query: LocationQueryRaw = {}
	const title = filters.title?.trim()
	if (title) query.title = title
	if (filters.status) query.status = filters.status
	if (filters.source) query.source = filters.source
	if (filters.asset) query.asset = filters.asset
	if (filters.tags.length) query.tag = [...filters.tags]
	if (filters.from) query.from = filters.from
	if (filters.to) query.to = filters.to
	if (filters.detection) query.detection = filters.detection
	if (filters.openedFrom) query.opened_from = filters.openedFrom
	if (filters.openedBefore) query.opened_before = filters.openedBefore
	return query
}

/** `query` with its filter keys replaced by `filters`'; every other key is kept. */
export function withFilters(query: LocationQuery, filters: AlertsFilters): LocationQueryRaw {
	const rest = Object.fromEntries(
		Object.entries(query).filter(([key]) => !(QUERY_KEYS as readonly string[]).includes(key))
	)
	return { ...rest, ...filtersToQuery(filters) }
}

/** Equal for filters that ask the same thing, whatever their spelling: what a list reloads on. */
export function filtersKey(filters: AlertsFilters): string {
	return JSON.stringify(filtersToQuery(filters))
}

/** The filters that currently restrict the list (the title aside): the links' first, then the menu's in order. */
export function activeFilterTypes(filters: AlertsFilters): AlertsFilterType[] {
	const active: Record<AlertsFilterType, boolean> = {
		status: !!filters.status,
		source: !!filters.source,
		asset: !!filters.asset,
		tag: filters.tags.length > 0,
		date: !!(filters.from || filters.to),
		detection: !!filters.detection,
		opened: !!(filters.openedFrom || filters.openedBefore)
	}
	return [...ALERTS_LINK_FILTER_TYPES, ...ALERTS_FILTER_TYPES].filter(type => active[type])
}

export function isLinkFilter(type: AlertsFilterType): type is AlertsLinkFilterType {
	return (ALERTS_LINK_FILTER_TYPES as AlertsFilterType[]).includes(type)
}

export function hasFilters(filters: AlertsFilters): boolean {
	return !!filters.title?.trim() || activeFilterTypes(filters).length > 0
}

/** `filters` with the menu filter `type` cleared. */
export function withoutFilter(filters: AlertsFilters, type: AlertsFilterType): AlertsFilters {
	switch (type) {
		case "tag":
			return { ...filters, tags: [] }
		case "date":
			return { ...filters, from: null, to: null }
		case "opened":
			return { ...filters, openedFrom: null, openedBefore: null }
		default:
			return { ...filters, [type]: null }
	}
}

/** How the "reached the SOC" window reads on its chip, each instant shown by `format`. */
export function openedLabel(filters: AlertsFilters, format: (iso: string) => string): string {
	const { openedFrom: from, openedBefore: before } = filters
	if (from && before) return `${format(from)} – ${format(before)}`
	if (from) return `since ${format(from)}`
	return before ? `before ${format(before)}` : ""
}

/** Local midnight of a `YYYY-MM-DD`, as epoch milliseconds (what the date picker holds). */
export function dayToTimestamp(day: string): number {
	const [year, month, date] = day.split("-").map(Number)
	return new Date(year, month - 1, date).getTime()
}

/** The local calendar day of an epoch-milliseconds instant, as `YYYY-MM-DD`. */
export function timestampToDay(timestamp: number): string {
	const date = new Date(timestamp)
	const pad = (value: number) => String(value).padStart(2, "0")
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export interface AlertsFilterParams {
	alert_title?: string
	status?: AlertStatus
	source?: string
	asset_name?: string
	tags?: string[]
	date_from?: string
	date_to?: string
	alert_name?: string
	opened_from?: string
	opened_before?: string
}

/**
 * The parameters of `GET /incidents/db_operations/alerts/filter` for `filters`. A day
 * range covers both days whole, from the first one's local midnight to the last
 * millisecond of the other, sent as UTC instants.
 */
export function filtersToParams(filters: AlertsFilters): AlertsFilterParams {
	const params: AlertsFilterParams = {}
	const title = filters.title?.trim()
	if (title) params.alert_title = title
	if (filters.status) params.status = filters.status
	if (filters.source) params.source = filters.source
	if (filters.asset) params.asset_name = filters.asset
	if (filters.tags.length) params.tags = [...filters.tags]
	if (filters.from) params.date_from = new Date(dayToTimestamp(filters.from)).toISOString()
	if (filters.to) {
		const [year, month, day] = filters.to.split("-").map(Number)
		params.date_to = new Date(year, month - 1, day, 23, 59, 59, 999).toISOString()
	}
	if (filters.detection) params.alert_name = filters.detection
	if (filters.openedFrom) params.opened_from = filters.openedFrom
	if (filters.openedBefore) params.opened_before = filters.openedBefore
	return params
}
