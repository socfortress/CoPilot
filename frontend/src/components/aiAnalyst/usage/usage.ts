// Pure helpers of the Talon v2 cost views (talon-analyst FR-COST-5 as built; CoPilot M5-9b).
//
// Money is the API's decimal string, shown as it came: nothing here adds, rounds or reformats an
// amount. Token counts and durations are integers, formatted for reading only.
import type { TalonUsageGroup, TalonUsageGroupBy } from "@/types/talonUsage"

/** talon-analyst `api/usage.py:MAX_DAYS`: both ends included. */
export const USAGE_MAX_DAYS = 366
/** The range the Usage tab opens on: the last 30 UTC days, today included. */
export const USAGE_DEFAULT_DAYS = 30

export const USAGE_GROUP_BY: { value: TalonUsageGroupBy; label: string }[] = [
	{ value: "customer", label: "Customer" },
	{ value: "model", label: "Model" },
	{ value: "provider", label: "Provider" },
	{ value: "role", label: "Role" },
	{ value: "stage", label: "Stage" },
	{ value: "day", label: "Day" },
	{ value: "user", label: "User" }
]

/** The non-admin's view (talon-analyst D51, review of #107), said beside the report. */
export const NON_ADMIN_USAGE_NOTE = "Investigations for your customers and your own chat."

const DAY = /^(\d{4})-(\d{2})-(\d{2})$/
const MS_PER_DAY = 86_400_000

function dayNumber(day: string): number | null {
	const match = DAY.exec(day)
	if (!match) return null
	const [, y, m, d] = match.map(Number)
	const time = Date.UTC(y, m - 1, d)
	const back = new Date(time)
	// 2026-02-30 is not a day (Date.UTC would roll it into March).
	if (back.getUTCFullYear() !== y || back.getUTCMonth() !== m - 1 || back.getUTCDate() !== d) return null
	return time / MS_PER_DAY
}

function isoDay(dayNo: number): string {
	return new Date(dayNo * MS_PER_DAY).toISOString().slice(0, 10)
}

/** The default range: `USAGE_DEFAULT_DAYS` UTC days ending today (UTC). */
export function defaultUsageRange(now: Date = new Date()): [string, string] {
	const today = Math.floor(now.getTime() / MS_PER_DAY)
	return [isoDay(today - (USAGE_DEFAULT_DAYS - 1)), isoDay(today)]
}

/** Why this range can't be asked for, in the words shown under the picker, or null. */
export function usageRangeProblem(from: string | null | undefined, to: string | null | undefined): string | null {
	const first = from ? dayNumber(from) : null
	const last = to ? dayNumber(to) : null
	if (first === null || last === null) return "Pick a first and a last day."
	if (first > last) return "The first day is after the last."
	if (last - first + 1 > USAGE_MAX_DAYS) return `At most ${USAGE_MAX_DAYS} days.`
	return null
}

/** How a group is named in the table and the chart. */
export function usageGroupLabel(group: Pick<TalonUsageGroup, "key" | "username">, groupBy: TalonUsageGroupBy): string {
	const key = group.key
	switch (groupBy) {
		case "customer":
			return key ?? "No customer (general chat)"
		case "user":
			if (key === null) return "Investigations (no user)"
			return group.username ? `${group.username} (${key})` : `User ${key}`
		case "day":
			return key ?? "No day"
		default:
			return key ?? "None"
	}
}

const COUNT = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 })

/** A token or response count (an integer), grouped for reading. */
export function formatCount(value: number | null | undefined): string {
	return typeof value === "number" && Number.isFinite(value) ? COUNT.format(value) : "—"
}

/** A duration in milliseconds, for reading (`850 ms`, `12.4 s`, `3 min 05 s`). */
export function formatDurationMs(ms: number | null | undefined): string {
	if (typeof ms !== "number" || !Number.isFinite(ms) || ms < 0) return "—"
	if (ms < 1000) return `${Math.round(ms)} ms`
	if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`
	const minutes = Math.floor(ms / 60_000)
	const seconds = Math.floor((ms % 60_000) / 1000)
	return `${minutes} min ${String(seconds).padStart(2, "0")} s`
}

/** A dollar amount exactly as the API wrote it (a decimal string), or a dash for none. */
export function formatUsd(value: string | null | undefined): string {
	return typeof value === "string" && value !== "" ? `$${value}` : "—"
}

function stageRank(stage: string): [number, string] {
	const match = /^S(\d+)(\D.*)?$/.exec(stage)
	return match ? [Number(match[1]), match[2] ?? ""] : [Number.MAX_SAFE_INTEGER, stage]
}

/** Stages in pipeline order: S0 … S10 (with `S5-escalation` after S5), then any other name. */
export function compareStages(a: string, b: string): number {
	const [na, ra] = stageRank(a)
	const [nb, rb] = stageRank(b)
	if (na !== nb) return na - nb
	return ra < rb ? -1 : ra > rb ? 1 : 0
}
