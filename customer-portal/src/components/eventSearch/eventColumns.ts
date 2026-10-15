import type { DisplayColumn, EventSearchResult } from "@/types/siem"
import dayjs from "@/utils/dayjs"

/**
 * The columns event search shows (#1258), described once for both the table and the CSV
 * export, so a file always holds what the user sees: the user's own columns, else the
 * SOC's for the source (`displayed_columns`), else the default layout.
 */

/**
 * A column: its header, the field it reads (`null` for a computed default column), and
 *  whether it holds an event time.
 */
export interface EventColumn {
	key: string
	label: string
	field: string | null
	time: boolean
	width?: number | null
}

/** Walks a dotted path ("agent.name") through a nested event. */
export function getNestedValue(obj: EventSearchResult, path: string): unknown {
	return path.split(".").reduce<unknown>((acc, segment) => {
		if (acc && typeof acc === "object") return (acc as Record<string, unknown>)[segment]
		return undefined
	}, obj)
}

/** A value as text: lists joined, objects as JSON, nothing as "". */
export function cellText(value: unknown): string {
	if (value === undefined || value === null || value === "") return ""
	if (Array.isArray(value)) return value.map(v => (v === null || v === undefined ? "" : String(v))).join(", ")
	if (typeof value === "object") return JSON.stringify(value)
	return String(value)
}

/** The source's `time_field`, or any key that names a timestamp. */
export function isTimeKey(key: string, timeField: string | null | undefined): boolean {
	return key === timeField || key.toLowerCase().includes("timestamp")
}

/** An event's time: the source's `time_field` first, then any timestamp-looking key. */
export function eventTime(row: EventSearchResult, timeField: string | null | undefined): unknown {
	const keys = [
		...(timeField ? [timeField] : []),
		...Object.keys(row).filter(k => k !== timeField && k.toLowerCase().includes("timestamp"))
	]
	for (const key of keys) {
		const value = getNestedValue(row, key)
		if (value !== undefined && value !== null && value !== "") return value
	}
	return undefined
}

/** Epoch milliseconds of an event time; an offset-less string is UTC (several sources write them). */
export function parseEventTime(value: unknown): number {
	if (value === undefined || value === null || value === "") return Number.NaN
	const parsed = typeof value === "number" ? dayjs(value) : dayjs.utc(`${value}`)
	return parsed.isValid() ? parsed.valueOf() : Number.NaN
}

export const DEFAULT_COLUMNS: EventColumn[] = [
	{ key: "Timestamp", label: "Timestamp", field: null, time: true, width: 160 },
	{ key: "Level", label: "Level", field: null, time: false, width: 60 },
	{ key: "Source", label: "Source", field: null, time: false },
	{ key: "Rule", label: "Rule", field: null, time: false }
]

/** The columns in force: the user's, else the SOC's for the source, else the default layout. */
export function resolveColumns(
	userColumns: DisplayColumn[] | null | undefined,
	sourceColumns: DisplayColumn[] | null | undefined,
	timeField: string | null | undefined
): EventColumn[] {
	const chosen = userColumns?.length ? userColumns : sourceColumns?.length ? sourceColumns : null
	if (!chosen) return DEFAULT_COLUMNS
	return chosen.map(c => ({
		key: c.key,
		label: c.label || c.key,
		field: c.key,
		time: isTimeKey(c.key, timeField),
		width: c.width ?? null
	}))
}

export function eventLevel(row: EventSearchResult): number | undefined {
	return row.rule_level ?? row.rule?.level
}

/** A column's raw value for one event: what the table formats and the CSV writes. */
export function columnValue(column: EventColumn, row: EventSearchResult, timeField: string | null | undefined): unknown {
	switch (column.field === null ? column.key : null) {
		case "Timestamp":
			return eventTime(row, timeField)
		case "Level":
			return eventLevel(row)
		case "Source":
			return row.agent_name || row.agent?.name
		case "Rule":
			return row.rule_description || row.rule?.description
		default:
			return getNestedValue(row, column.field ?? column.key)
	}
}

/**
 * The field a column reads, as an analyst would name it: its own for a picked column, the
 * one `columnValue` reads first for a column of the default layout.
 */
export function columnSource(column: EventColumn, timeField: string | null | undefined): string {
	if (column.field !== null) return column.field
	switch (column.key) {
		case "Timestamp":
			return timeField || "timestamp"
		case "Level":
			return "rule_level"
		case "Source":
			return "agent_name"
		case "Rule":
			return "rule_description"
		default:
			return column.key
	}
}

/**
 * The CSV of `events` in `columns`: a header per column, then one row per event. Times are
 * written as ISO 8601 in UTC — what a spreadsheet or a script reads without guessing the
 * viewer's timezone; a time that cannot be read is kept as it came.
 */
export function eventsToCsv(
	columns: EventColumn[],
	events: EventSearchResult[],
	timeField: string | null | undefined
): { headers: string[]; rows: string[][] } {
	const headers = columns.map(c => c.label)
	const rows = events.map(row =>
		columns.map(column => {
			const value = columnValue(column, row, timeField)
			if (column.time) {
				const epoch = parseEventTime(value)
				return Number.isNaN(epoch) ? cellText(value) : new Date(epoch).toISOString()
			}
			return cellText(value)
		})
	)
	return { headers, rows }
}

/** A file name for an export: the source, and when. */
export function eventsFilename(sourceName: string, now = new Date()): string {
	const stamp = now.toISOString().slice(0, 19).replace(/[:T]/g, "-")
	return `events-${sourceName.replace(/[^\w.-]+/g, "_")}-${stamp}.csv`
}
