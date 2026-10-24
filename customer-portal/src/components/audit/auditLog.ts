import type { LocationQuery, LocationQueryRaw, LocationQueryValue, RouteLocationRaw } from "vue-router"
import type { AuditActor, AuditCategory, AuditEntry, AuditQuery, AuditTarget } from "@/types/audit"
import { dayToTimestamp, isDay } from "@/components/alerts/filters/alertsFilters"
import { workflowStatusLabel } from "@/utils/workflowStatus"

/**
 * Pure presentation logic of the Audit Log page (#1298): what lives in the URL, how an entry
 * reads, and where a click on its target leads. Kept out of the component so it is testable.
 *
 * In the URL: `?category=cases&user=12&from=2026-10-01&to=2026-10-07&customer=ACME&page=2`,
 * defaults left out. Days are the viewer's local calendar days; the API gets local midnight of
 * the first and of the day after the last, as UTC instants. Every change replaces the entry,
 * like every filter in the portal.
 */

export const PAGE_SIZE = 25

export const CATEGORY_LABELS: Record<AuditCategory, string> = {
	alerts: "Alerts",
	cases: "Cases",
	reports: "Reports",
	users: "Users",
	account: "Sign-ins and accounts"
}

export const CATEGORIES = Object.keys(CATEGORY_LABELS) as AuditCategory[]

export const CATEGORY_ICONS: Record<AuditCategory, string> = {
	alerts: "carbon:warning-alt",
	cases: "carbon:portfolio",
	reports: "carbon:report",
	users: "carbon:user-multiple",
	account: "carbon:login"
}

export interface AuditState {
	category: AuditCategory | null
	userId: number | null
	from: string | null
	to: string | null
	customer: string | null
	page: number
}

export const EMPTY_STATE: AuditState = Object.freeze({
	category: null,
	userId: null,
	from: null,
	to: null,
	customer: null,
	page: 1
})

type QueryValue = LocationQueryValue | LocationQueryValue[] | undefined

function single(value: QueryValue): string | null {
	const raw = Array.isArray(value) ? value[0] : value
	return typeof raw === "string" && raw.trim() ? raw.trim() : null
}

function positiveInt(value: string | null): number | null {
	if (!value || !/^\d{1,9}$/.test(value)) return null
	const number = Number(value)
	return number >= 1 ? number : null
}

/** The state a query asks for. Anything unreadable is dropped rather than sent. */
export function stateFromQuery(query: LocationQuery): AuditState {
	const category = single(query.category)
	let from = single(query.from)
	let to = single(query.to)
	from = isDay(from) ? from : null
	to = isDay(to) ? to : null
	// A hand-edited link with the days the wrong way round still means that range.
	if (from && to && from > to) [from, to] = [to, from]
	return {
		category: category && Object.hasOwn(CATEGORY_LABELS, category) ? (category as AuditCategory) : null,
		userId: positiveInt(single(query.user)),
		from,
		to,
		customer: single(query.customer),
		page: positiveInt(single(query.page)) ?? 1
	}
}

/** `query` with the state written (defaults left out); every other key is kept. */
export function withState(query: LocationQuery, state: AuditState): LocationQueryRaw {
	const { category: _c, user: _u, from: _f, to: _t, customer: _cu, page: _p, ...rest } = query
	const next: LocationQueryRaw = { ...rest }
	if (state.category) next.category = state.category
	if (state.userId) next.user = String(state.userId)
	if (state.from) next.from = state.from
	if (state.to) next.to = state.to
	if (state.customer) next.customer = state.customer
	if (state.page > 1) next.page = String(state.page)
	return next
}

/** A filter changed: back to the first page. */
export function withFilter(state: AuditState, change: Partial<Omit<AuditState, "page">>): AuditState {
	return { ...state, ...change, page: 1 }
}

export function hasFilters(state: AuditState): boolean {
	return !!(state.category || state.userId || state.from || state.to || state.customer)
}

/** The day after a `YYYY-MM-DD`, at local midnight, as epoch milliseconds (DST-safe). */
function nextDayTimestamp(day: string): number {
	const [year, month, date] = day.split("-").map(Number)
	return new Date(year, month - 1, date + 1).getTime()
}

/** The API's query for a state: whole local days, `until` exclusive. */
export function stateToQuery(state: AuditState, pageSize = PAGE_SIZE): AuditQuery {
	return {
		category: state.category,
		userId: state.userId,
		since: state.from ? new Date(dayToTimestamp(state.from)).toISOString() : null,
		until: state.to ? new Date(nextDayTimestamp(state.to)).toISOString() : null,
		page: state.page,
		pageSize
	}
}

/** Who did it, in words: one of the customer's users by name, the SOC never by name. */
export function actorLabel(actor: AuditActor): string {
	if (actor.kind === "member") return actor.username ?? "A portal user"
	if (actor.kind === "soc") return "SOC"
	if (actor.kind === "other") return "Another portal user"
	return "Unknown"
}

/** What it was done to, in words. */
export function targetLabel(target: AuditTarget | null): string {
	if (!target) return ""
	if (target.type === "user") return target.label ?? target.id
	const kind = { alert: "Alert", case: "Case", report: "Report" }[target.type]
	return `${kind} #${target.id}${target.label ? ` · ${target.label}` : ""}`
}

/** An alert or a case the log names, opened in its modal (whose header leads to its page). */
export interface AuditEntityRef {
	type: "alert" | "case"
	id: number
}

/** The alert or case a target names, by id; anything else (a report, a user) has no modal. */
export function targetEntity(entry: AuditEntry): AuditEntityRef | null {
	const target = entry.target
	if (!target || (target.type !== "alert" && target.type !== "case") || !/^\d{1,9}$/.test(target.id)) return null
	return { type: target.type, id: Number(target.id) }
}

/**
 * Where a report target leads, while it still exists: the reports list (a report has no modal). An
 * alert or a case opens in its modal instead (`targetEntity`); a deleted report or a user, nowhere.
 */
export function targetRoute(entry: AuditEntry): RouteLocationRaw | null {
	if (entry.target?.type === "report" && entry.action !== "report.delete") return { name: "ReportsList" }
	return null
}

/** A status change, in the portal's words ("Waiting on you" for the SOC's wait). */
export function changeLabel(entry: AuditEntry): string {
	if (!entry.from_value && !entry.to_value) return ""
	const from = entry.from_value ? workflowStatusLabel(entry.from_value) : "—"
	const to = entry.to_value ? workflowStatusLabel(entry.to_value) : "—"
	return `${from} → ${to}`
}

/** How long the log goes back. */
export function retentionText(days: number): string {
	if (!days) return "Kept for as long as your SOC keeps its audit log."
	return `Kept for ${days} ${days === 1 ? "day" : "days"}: older entries are removed.`
}

export function exportFilename(now = new Date()): string {
	const pad = (value: number) => String(value).padStart(2, "0")
	return `audit-log-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}.csv`
}
