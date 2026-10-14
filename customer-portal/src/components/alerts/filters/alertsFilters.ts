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
}

/** The filters the "Add filter" menu offers; the title search is always shown. */
export type AlertsFilterType = "status" | "source" | "asset" | "tag" | "date"

export const ALERTS_FILTER_TYPES: AlertsFilterType[] = ["status", "source", "asset", "tag", "date"]

export const ALERTS_FILTER_LABELS: Record<AlertsFilterType, string> = {
	status: "Status",
	source: "Source",
	asset: "Asset",
	tag: "Tag",
	date: "Created"
}

const QUERY_KEYS = ["title", "status", "source", "asset", "tag", "from", "to"] as const

export const EMPTY_ALERTS_FILTERS: AlertsFilters = Object.freeze({
	title: null,
	status: null,
	source: null,
	asset: null,
	tags: [],
	from: null,
	to: null
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

/** The filters a query asks for. Anything unreadable is ignored rather than sent. */
export function filtersFromQuery(query: LocationQuery): AlertsFilters {
	const status = single(query.status)
	let from = single(query.from)
	let to = single(query.to)
	from = isDay(from) ? from : null
	to = isDay(to) ? to : null
	// A hand-edited link with the days the wrong way round still means that range.
	if (from && to && from > to) [from, to] = [to, from]

	return {
		title: single(query.title),
		status: isStatus(status) ? status : null,
		source: single(query.source),
		asset: single(query.asset),
		tags: [...new Set(values(query.tag))],
		from,
		to
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

/** The menu filters that currently restrict the list, in menu order. */
export function activeFilterTypes(filters: AlertsFilters): AlertsFilterType[] {
	const active: Record<AlertsFilterType, boolean> = {
		status: !!filters.status,
		source: !!filters.source,
		asset: !!filters.asset,
		tag: filters.tags.length > 0,
		date: !!(filters.from || filters.to)
	}
	return ALERTS_FILTER_TYPES.filter(type => active[type])
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
		default:
			return { ...filters, [type]: null }
	}
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
	return params
}
