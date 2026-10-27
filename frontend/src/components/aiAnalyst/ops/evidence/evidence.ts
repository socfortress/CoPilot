// The Ops drawer's evidence views (OP-3): pure readers of each job's evidence, the unit formatters, and
// `disk_forecast`'s daily points from the job's runs. The shapes are talon-analyst's job modules'
// (`src/talon/ops/jobs/*.py`, each `Candidate(..., evidence=...)`), as CoPilot relays them (a bounded,
// cleaned copy). Every field is optional and may be malformed: a reader returns null when the fields
// its view needs don't parse, and the drawer falls back to the generic list. Nothing here is guessed:
// a value Talon didn't send is shown as missing, never filled in.
//
// Everything a view shows is bound as text. Nothing here builds markup, and no model text (`why`,
// `recommendation`) is read: only the evidence, which Talon's code wrote.
import type { RouteLocationRaw } from "vue-router"
import type { TalonOpsEvidenceValue, TalonOpsRun } from "@/types/talonOps"
import { formatTime } from "../../health/health"
import { isLinkId, kindLabel } from "../ops"

export type Evidence = Record<string, TalonOpsEvidenceValue>

/** OpenSearch's GB, as Talon computes them: 1024-based (`cluster_health.GIB`). */
export const GIB = 1024 ** 3
export const NONE = "—"
const DAY_MS = 24 * 60 * 60 * 1000

// ── reading values ────────────────────────────────────────────────────────────

export function num(value: unknown): number | null {
	return typeof value === "number" && Number.isFinite(value) ? value : null
}

export function str(value: unknown): string | null {
	return typeof value === "string" && value !== "" ? value : null
}

export function bool(value: unknown): boolean | null {
	return typeof value === "boolean" ? value : null
}

export function obj(value: unknown): Evidence | null {
	return value !== null && typeof value === "object" && !Array.isArray(value) ? (value as Evidence) : null
}

export function list(value: unknown): TalonOpsEvidenceValue[] | null {
	return Array.isArray(value) ? value : null
}

function strings(value: unknown): string[] | null {
	const items = list(value)
	if (!items) return null
	const out = items.filter((v): v is string => typeof v === "string" && v !== "")
	return out.length === items.length ? out : null
}

/** An ISO time in ms (a fraction past the millisecond cut), or null. */
export function isoMs(value: unknown): number | null {
	if (typeof value !== "string" || value.length > 64) return null
	if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) return null
	const ms = Date.parse(value.replace(/(\.\d{3})\d+/, "$1"))
	return Number.isFinite(ms) ? ms : null
}

// ── units ─────────────────────────────────────────────────────────────────────

function fixed(value: number, digits: number): string {
	return value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

/** GB with 2 decimals under 100, else 1 ("12.34 GB", "512.3 GB"). */
export function gbText(gb: number | null | undefined): string {
	if (num(gb) === null) return NONE
	const value = gb as number
	return `${fixed(value, Math.abs(value) < 100 ? 2 : 1)} GB`
}

/** Bytes as GB (1024-based, as Talon's evidence). */
export function bytesText(bytes: number | null | undefined): string {
	return num(bytes) === null ? NONE : gbText((bytes as number) / GIB)
}

/** GB per day, signed when it shrinks. */
export function gbPerDayText(gb: number | null | undefined): string {
	return num(gb) === null ? NONE : `${gbText(gb)}/day`
}

/** A ratio (0.824) as a percentage ("82.4%"). */
export function ratioText(ratio: number | null | undefined): string {
	return num(ratio) === null ? NONE : pctText((ratio as number) * 100)
}

/** A percentage (82.4) as text ("82.4%"). */
export function pctText(pct: number | null | undefined): string {
	if (num(pct) === null) return NONE
	const value = pct as number
	return `${fixed(value, Number.isInteger(value) ? 0 : 1)}%`
}

/** Days, to one decimal ("4.5 days", "1 day"). */
export function daysText(days: number | null | undefined): string {
	if (num(days) === null) return NONE
	const rounded = Math.round((days as number) * 10) / 10
	const text = Number.isInteger(rounded) ? String(rounded) : fixed(rounded, 1)
	return `${text} ${rounded === 1 ? "day" : "days"}`
}

/** Hours, to one decimal. */
export function hoursText(hours: number | null | undefined): string {
	if (num(hours) === null) return NONE
	const rounded = Math.round((hours as number) * 10) / 10
	const text = Number.isInteger(rounded) ? String(rounded) : fixed(rounded, 1)
	return `${text} ${rounded === 1 ? "hour" : "hours"}`
}

export function minutesText(minutes: number | null | undefined): string {
	if (num(minutes) === null) return NONE
	const value = Math.round(minutes as number)
	return `${value.toLocaleString()} ${value === 1 ? "minute" : "minutes"}`
}

export function countText(value: number | null | undefined): string {
	return num(value) === null ? NONE : (value as number).toLocaleString()
}

export function yesNo(value: unknown): string {
	return value === true ? "yes" : value === false ? "no" : NONE
}

export interface TimeTextParts {
	/** Local time, for the page. */
	local: string
	/** The same instant in UTC, for the tooltip. */
	utc: string
	/** "3 days ago", "in 2 hours". */
	relative: string
}

/** "2026-10-24 06:00 UTC". */
export function utcText(ms: number): string {
	return `${new Date(ms).toISOString().slice(0, 16).replace("T", " ")} UTC`
}

/** "just now", "5 minutes ago", "3 days ago", "in 2 hours". */
export function relativeText(ms: number, now = Date.now()): string {
	const diff = ms - now
	const abs = Math.abs(diff)
	if (abs < 60_000) return "just now"
	const units: [number, string][] = [
		[DAY_MS, "day"],
		[60 * 60 * 1000, "hour"],
		[60_000, "minute"]
	]
	const [size, name] = units.find(([unit]) => abs >= unit) as [number, string]
	const n = Math.floor(abs / size)
	const text = `${n} ${name}${n === 1 ? "" : "s"}`
	return diff < 0 ? `${text} ago` : `in ${text}`
}

/** An ISO time as local time, UTC (the tooltip) and relative; null when it doesn't parse. */
export function timeParts(iso: unknown, now = Date.now()): TimeTextParts | null {
	const ms = isoMs(iso)
	if (ms === null) return null
	return { local: formatTime(iso as string), utc: utcText(ms), relative: relativeText(ms, now) }
}

// ── key figures (cluster_health, silent_log_sources, and the views' own) ─────

export type Unit = "gb" | "gb_day" | "pct" | "ratio" | "days" | "hours" | "minutes" | "count" | "time" | "bool" | "text"

export interface Figure {
	key: string
	label: string
	/** The value as text, with its unit. */
	text: string
	/** For a time: the UTC text (the tooltip). */
	title?: string
}

/** One value as text in its unit; null when it isn't of that unit's type. */
export function unitText(value: unknown, unit: Unit): { text: string; title?: string } | null {
	switch (unit) {
		case "gb":
			return num(value) === null ? null : { text: gbText(value as number) }
		case "gb_day":
			return num(value) === null ? null : { text: gbPerDayText(value as number) }
		case "pct":
			return num(value) === null ? null : { text: pctText(value as number) }
		case "ratio":
			return num(value) === null ? null : { text: ratioText(value as number) }
		case "days":
			return num(value) === null ? null : { text: daysText(value as number) }
		case "hours":
			return num(value) === null ? null : { text: hoursText(value as number) }
		case "minutes":
			return num(value) === null ? null : { text: minutesText(value as number) }
		case "count":
			return num(value) === null ? null : { text: countText(value as number) }
		case "time": {
			const parts = timeParts(value)
			return parts ? { text: `${parts.local} (${parts.relative})`, title: parts.utc } : null
		}
		case "bool":
			return bool(value) === null ? null : { text: yesNo(value) }
		case "text":
			return str(value) === null && num(value) === null ? null : { text: String(value) }
	}
}

/** A figure's spec: a key (or a dotted path one level down), its label and unit. */
export type FigureSpec = [path: string, label: string, unit: Unit]

function at(evidence: Evidence, path: string): unknown {
	const [head, ...rest] = path.split(".")
	let value: unknown = evidence[head]
	for (const key of rest) value = obj(value)?.[key]
	return value
}

/** The figures of `specs` the evidence has, in order; those missing or malformed are left out. */
export function figures(evidence: Evidence | null | undefined, specs: FigureSpec[]): Figure[] {
	if (!evidence) return []
	const out: Figure[] = []
	for (const [path, label, unit] of specs) {
		const shown = unitText(at(evidence, path), unit)
		if (shown) out.push({ key: path, label, ...shown })
	}
	return out
}

/** `cluster_health`'s figures, over its six kinds (a kind has only some of them). */
export const CLUSTER_HEALTH_FIGURES: FigureSpec[] = [
	["cluster_name", "Cluster", "text"],
	["status", "Status", "text"],
	["node", "Node", "text"],
	["used_pct", "Disk used", "pct"],
	["avail_gb", "Disk available", "gb"],
	["total_gb", "Disk total", "gb"],
	["indices_gb", "Indices on the node", "gb"],
	["level", "Watermark reached", "text"],
	["thresholds_used_pct.low", "Low watermark", "pct"],
	["thresholds_used_pct.high", "High watermark", "pct"],
	["thresholds_used_pct.flood_stage", "Flood stage", "pct"],
	["threshold_enabled", "Disk thresholds on", "bool"],
	["number_of_data_nodes", "Data nodes", "count"],
	["data_nodes", "Data nodes", "count"],
	["highest_recent", "Data nodes at most, recently", "count"],
	["nodes", "Nodes", "count"],
	["unassigned_shards", "Unassigned shards", "count"],
	["unassigned_primaries", "Unassigned primaries", "count"],
	["unassigned_replicas", "Unassigned replicas", "count"],
	["unhealthy_minutes", "Unhealthy for", "minutes"],
	["unhealthy_since", "Unhealthy since", "time"],
	["index_family", "Index family", "text"],
	["reason", "Reason", "text"],
	["primaries", "Primaries", "count"],
	["replicas", "Replicas", "count"],
	["indices", "Indices", "count"],
	["oldest_unassigned_at", "Oldest unassigned", "time"],
	["single_node", "Single data node", "bool"],
	["shards", "Shards", "count"],
	["limit", "Shard limit", "count"],
	["used_ratio", "Of the limit", "ratio"],
	["max_shards_per_node", "Shards per node (limit)", "count"],
	["policy_id", "ISM policy", "text"],
	["state", "State", "text"],
	["failed_indices", "Failed indices", "count"],
	["retry_failed", "Retries failed", "count"]
]

/** `silent_log_sources`' figures. */
export const SILENT_LOG_SOURCES_FIGURES: FigureSpec[] = [
	["source", "Source", "text"],
	["event_type", "Event type", "text"],
	["index_pattern", "Index pattern", "text"],
	["last_hour", "Events in the last hour", "count"],
	["median", "Usual for this hour (median)", "count"],
	["baseline", "Baseline", "text"],
	["detected_median", "Median when detected", "count"],
	["newest_event", "Newest event", "time"],
	["hours_since_newest", "Since the newest event", "hours"],
	["time_field", "Time field", "text"]
]

// ── agent_hygiene ─────────────────────────────────────────────────────────────

export interface AgentRow {
	id: string
	hostname: string | null
	version: string | null
	critical: boolean | null
	/** The agent's page, when its id is a plain id (`LINK_ID`); else none. */
	to: RouteLocationRaw | null
}

export interface AgentHygieneView {
	rows: AgentRow[]
	more: number
	/** Whether the version column applies (a version per agent, or the group's). */
	hasVersion: boolean
	figures: Figure[]
}

function agentRows(value: unknown, versionOf: (id: string) => string | null): AgentRow[] | null {
	const items = list(value)
	if (!items) return null
	const rows: AgentRow[] = []
	for (const item of items) {
		const agent = obj(item)
		const id = str(agent?.agent_id)
		if (!agent || id === null) continue
		rows.push({
			id,
			hostname: str(agent.agent_name),
			version: versionOf(id),
			critical: bool(agent.critical_asset),
			to: isLinkId(id) ? { name: "Agent", params: { id } } : null
		})
	}
	return rows.length ? rows : null
}

/**
 * `agent_hygiene`: the group's agents (`sample_agents`, or `behind.sample_agents` for
 * `velociraptor_version`) with each one's version: the group's `agent_version` (`wazuh_version`) or the
 * agent's in `behind_versions` (`velociraptor_version`); `velociraptor_missing` has none.
 */
export function agentHygieneView(evidence: Evidence | null | undefined, kind: string): AgentHygieneView | null {
	if (!evidence) return null
	const behind = obj(evidence.behind)
	const nested = kind === "velociraptor_version" && behind && Array.isArray(behind.sample_agents)
	const group = nested ? (behind as Evidence) : evidence
	const groupVersion = kind === "wazuh_version" ? str(evidence.agent_version) : null
	const perAgent = kind === "velociraptor_version" ? obj(evidence.behind_versions) : null
	const rows = agentRows(group.sample_agents, id => (perAgent ? str(perAgent[id]) : groupVersion))
	if (!rows) return null
	const more = num(group.agents_more)
	return {
		rows,
		more: more !== null && more > 0 ? more : 0,
		hasVersion: groupVersion !== null || perAgent !== null,
		figures: [
			...figures(evidence, [
				["manager_version", "Manager version", "text"],
				["agent_version", "Agent version", "text"],
				["newest_version", "Newest client version", "text"],
				["active_agents", "Active agents", "count"]
			]),
			...figures(group, [
				["agents", "Agents in this group", "count"],
				["critical_assets", "Critical assets among them", "count"]
			])
		]
	}
}

// ── quiet_endpoints ───────────────────────────────────────────────────────────

export interface LastSeen {
	label: string
	time: TimeTextParts | null
	days: number | null
}

export interface QuietEndpointsView {
	conditions: { kind: string; label: string }[]
	seen: LastSeen[]
	figures: Figure[]
}

/** `quiet_endpoints`: the agent's conditions and when Wazuh and Velociraptor last saw it. */
export function quietEndpointsView(evidence: Evidence | null | undefined, now = Date.now()): QuietEndpointsView | null {
	if (!evidence) return null
	const conditions = strings(evidence.conditions)
	const seen: LastSeen[] = [
		{
			label: "Wazuh",
			time: timeParts(evidence.wazuh_last_seen, now),
			days: num(evidence.wazuh_days_quiet)
		},
		{
			label: "Velociraptor",
			time: timeParts(evidence.velociraptor_last_seen, now),
			days: num(evidence.velociraptor_days_quiet)
		}
	]
	if (!conditions && seen.every(s => s.time === null && s.days === null)) return null
	return {
		conditions: (conditions ?? []).map(kind => ({ kind, label: kindLabel(kind) })),
		seen,
		figures: figures(evidence, [
			["agent_id", "Agent", "text"],
			["agent_name", "Hostname", "text"],
			["os", "OS", "text"],
			["critical_asset", "Critical asset", "bool"],
			["wazuh_status", "Wazuh status", "text"],
			["velociraptor_id", "Velociraptor client", "text"]
		])
	}
}

// ── mapping_drift ─────────────────────────────────────────────────────────────

export type MappingDriftView =
	| {
			kind: "field_limit"
			used: number
			limit: number
			/** 0..100, for the bar (capped at 100). */
			percent: number
			lowerBound: boolean
			figures: Figure[]
	  }
	| { kind: "type_conflict"; rows: { field: string; types: string; talon: boolean }[]; more: number; figures: Figure[] }
	| { kind: "field_growth"; before: number; after: number; figures: Figure[] }
	| { kind: "talon_fields"; rows: { field: string; problem: string; mapped: string; needs: string }[]; more: number; figures: Figure[] }

const PATTERN_FIGURES: FigureSpec[] = [
	["index_pattern", "Index pattern", "text"],
	["index", "Index", "text"]
]

function typesText(value: unknown): string | null {
	const items = strings(value)
	if (items) return items.length ? items.join(", ") : null
	return str(value)
}

/** `mapping_drift`, by kind: the field limit as a bar, conflicts and Talon's fields as tables, growth as before → after. */
export function mappingDriftView(evidence: Evidence | null | undefined, kind: string): MappingDriftView | null {
	if (!evidence) return null
	if (kind === "field_limit") {
		const used = num(evidence.mapped_fields)
		const limit = num(evidence.total_fields_limit)
		if (used === null || limit === null || limit <= 0) return null
		return {
			kind,
			used,
			limit,
			percent: Math.min(100, Math.max(0, (used / limit) * 100)),
			lowerBound: evidence.lower_bound === true,
			figures: figures(evidence, [
				...PATTERN_FIGURES,
				["field_count", "Fields", "count"],
				["object_fields", "Object fields", "count"],
				["number_of_shards", "Shards", "count"],
				["number_of_replicas", "Replicas", "count"],
				["creation_date", "Index created", "time"]
			])
		}
	}
	if (kind === "type_conflict") {
		const conflicts = obj(evidence.conflicts)
		if (!conflicts) return null
		const talon = new Set(strings(evidence.talon_fields_conflicting) ?? [])
		const rows = Object.entries(conflicts)
			.map(([field, types]) => ({ field, types: typesText(types), talon: talon.has(field) }))
			.filter((row): row is { field: string; types: string; talon: boolean } => row.types !== null)
		if (!rows.length) return null
		const total = num(evidence.conflicts_total)
		return {
			kind,
			rows,
			more: total !== null && total > rows.length ? total - rows.length : 0,
			figures: figures(evidence, [
				["index_pattern", "Index pattern", "text"],
				["window_days", "Indices of the last", "days"],
				["conflicts_total", "Fields in conflict", "count"]
			])
		}
	}
	if (kind === "field_growth") {
		const after = num(evidence.family_field_count)
		const before = num(evidence.baseline_family_field_count)
		if (after === null || before === null) return null
		return {
			kind,
			before,
			after,
			figures: figures(evidence, [
				...PATTERN_FIGURES,
				["growth", "Growth", "ratio"],
				["baseline_age_days", "Baseline from", "days"],
				["baseline_tick", "Baseline run", "time"]
			]).map(f => (f.key === "baseline_age_days" ? { ...f, text: `${f.text} ago` } : f))
		}
	}
	if (kind === "talon_fields") {
		const items = list(evidence.problems)
		if (!items) return null
		const rows = []
		for (const item of items) {
			const problem = obj(item)
			const field = str(problem?.field)
			const what = str(problem?.problem)
			if (!problem || field === null || what === null) continue
			const mapped = obj(problem.mapped)
			const mappedText = mapped
				? Object.entries(mapped)
						.map(([name, types]) => `${name}: ${typesText(types) ?? NONE}`)
						.join("; ")
				: ""
			rows.push({
				field,
				problem: what === "missing" ? "Missing" : what === "type" ? "Wrong type" : what,
				mapped: mappedText || NONE,
				needs: typesText(problem.needs) ?? NONE
			})
		}
		if (!rows.length) return null
		const total = num(evidence.problems_total)
		return {
			kind,
			rows,
			more: total !== null && total > rows.length ? total - rows.length : 0,
			figures: figures(evidence, PATTERN_FIGURES)
		}
	}
	return null
}

// ── bars (storage_usage, noisy_events) ────────────────────────────────────────

export interface Bar {
	label: string
	value: number
	text: string
	/** 0..100 of the largest bar in its group. */
	width: number
}

export interface BarGroup {
	title: string
	bars: Bar[]
}

/** Bars scaled to the group's largest value (a negative or missing value gets no bar). */
export function bars(title: string, items: { label: string; value: number | null }[], text: (v: number) => string): BarGroup {
	const kept = items.filter((i): i is { label: string; value: number } => i.value !== null && i.value >= 0)
	const max = Math.max(0, ...kept.map(i => i.value))
	return {
		title,
		bars: kept.map(i => ({ label: i.label, value: i.value, text: text(i.value), width: max > 0 ? (i.value / max) * 100 : 0 }))
	}
}

export interface StorageUsageView {
	groups: BarGroup[]
	more: number
	figures: Figure[]
}

/** `storage_usage`: per family (index pattern), GB stored and GB per day over 7 days, as bars. */
export function storageUsageView(evidence: Evidence | null | undefined): StorageUsageView | null {
	if (!evidence) return null
	const families: { label: string; size: number | null; rate: number | null }[] = []
	for (const item of list(evidence.families) ?? []) {
		const family = obj(item)
		const label = str(family?.index_pattern)
		if (!family || label === null) continue
		const size = num(family.size_gb)
		const rate = num(family.gb_per_day_7d)
		if (size === null && rate === null) continue
		families.push({ label, size, rate })
	}
	if (!families.length) return null
	const more = num(evidence.families_more)
	return {
		groups: [
			bars("GB stored", families.map(f => ({ label: f.label, value: f.size })), gbText),
			bars("GB per day (last 7 days)", families.map(f => ({ label: f.label, value: f.rate })), gbPerDayText)
		].filter(g => g.bars.length),
		more: more !== null && more > 0 ? more : 0,
		figures: figures(evidence, [
			["total_size_gb", "Stored in total", "gb"],
			["gb_per_day_7d", "Ingest, last 7 days", "gb_day"],
			["gb_per_day_28d", "Ingest, last 28 days", "gb_day"],
			["growth", "7-day rate against the 28-day rate", "ratio"],
			["history_days", "History", "days"],
			["indices", "Indices", "count"],
			["total_docs", "Documents", "count"],
			["replicas_included", "Replicas in the rates", "bool"]
		])
	}
}

export interface NoisyEventsView {
	share: number
	groups: BarGroup[]
	figures: Figure[]
}

/** `noisy_events`: the candidate's share of its pattern's events, and its GB per day against the floor and the customer's. */
export function noisyEventsView(evidence: Evidence | null | undefined): NoisyEventsView | null {
	if (!evidence) return null
	const share = num(evidence.share)
	const gb = num(evidence.estimated_gb_per_day)
	if (share === null || gb === null || share < 0) return null
	return {
		share: Math.min(100, share * 100),
		groups: [
			bars(
				"GB per day",
				[
					{ label: "This candidate", value: gb },
					{ label: "The floor it passed", value: num(evidence.gb_floor) },
					{ label: "The customer, all measured", value: num(evidence.customer_gb_per_day) }
				],
				gbPerDayText
			)
		],
		figures: figures(evidence, [
			["index_pattern", "Index pattern", "text"],
			["rule_id", "Rule", "text"],
			["rule_level", "Rule level", "count"],
			["data_win_system_eventID", "Event id", "text"],
			["data_win_eventdata_image", "Image", "text"],
			["events_7d", "Events, last 7 days", "count"],
			["pattern_events_7d", "Pattern's events, last 7 days", "count"],
			["hosts", "Hosts", "count"],
			["first_seen", "First seen", "time"],
			["critical_binary", "Critical binary", "bool"],
			["writable_path", "Writable path", "bool"]
		])
	}
}

// ── exclusion_candidates ──────────────────────────────────────────────────────

export interface Guard {
	key: string
	label: string
	/** True: passed (none found); false: found some (`count`); null: not recorded. */
	passed: boolean | null
	count: number | null
}

export interface ExclusionView {
	verdicts: Figure[]
	guards: Guard[]
	/** `host_scoped` is false: the rule applies to every agent on the Wazuh manager. */
	managerWide: boolean
	asset: string | null
	figures: Figure[]
}

/** The rule-wide guards: none of these on the rule, on any asset, over the lookback. */
const GUARDS: [key: string, label: string][] = [
	["true_positive", "No true-positive verdict on the rule"],
	["escalated", "No escalated alert on the rule"],
	["cases", "No alert of the rule linked to a case"],
	["bas_alerts", "No BAS or simulation word in the rule's alerts"],
	["critical_asset_alerts", "No alert of the rule on a critical asset"]
]

/**
 * `exclusion_candidates`: the group's verdicts (CoPilot's are TRUE_POSITIVE and FALSE_POSITIVE only, so
 * the true positives are the verdicted alerts less the false positives, and the alerts without a
 * verdict are undetermined), the rule-wide guards, and whether the rule is manager-wide.
 */
export function exclusionView(evidence: Evidence | null | undefined): ExclusionView | null {
	if (!evidence) return null
	const alerts = num(evidence.alerts)
	const verdicted = num(evidence.verdicted)
	const fp = num(evidence.false_positive_verdicts)
	if (alerts === null && verdicted === null && fp === null) return null
	const tp = verdicted !== null && fp !== null && verdicted >= fp ? verdicted - fp : null
	const none = alerts !== null && verdicted !== null && alerts >= verdicted ? alerts - verdicted : null
	const verdicts: Figure[] = [
		{ key: "false_positive", label: "False positive", text: countText(fp) },
		{ key: "true_positive", label: "True positive", text: countText(tp) },
		{ key: "undetermined", label: "Undetermined (no verdict)", text: countText(none) }
	]
	const rule = obj(evidence.rule_wide)
	const lookback = num(rule?.lookback_days)
	const guards: Guard[] = rule
		? GUARDS.filter(([key]) => key in rule).map(([key, label]) => {
				const count = num(rule[key])
				return {
					key,
					label: lookback !== null ? `${label} (${daysText(lookback)})` : label,
					passed: count === null ? null : count === 0,
					count
				}
			})
		: []
	return {
		verdicts,
		guards,
		managerWide: evidence.host_scoped === false,
		asset: str(evidence.asset_name),
		figures: figures(evidence, [
			["signal_label", "Signal", "text"],
			["alert_name", "Alert", "text"],
			["asset_name", "Asset", "text"],
			["rule_id", "Rule", "text"],
			["rule_level", "Rule level", "count"],
			["alerts", "Alerts", "count"],
			["closed", "Closed", "count"],
			["window_days", "Window", "days"],
			["first_alert", "First alert", "time"],
			["last_alert", "Last alert", "time"],
			["last_false_positive_verdict", "Last false-positive verdict", "time"],
			["sampled_events", "Events sampled", "count"]
		])
	}
}

// ── disk_forecast ─────────────────────────────────────────────────────────────

export interface DiskPoint {
	/** The sample's time (ms). */
	t: number
	/** Bytes. */
	used: number
	total: number
}

export const WATERMARKS = [
	{ key: "low", label: "Low watermark" },
	{ key: "high", label: "High watermark" },
	{ key: "flood_stage", label: "Flood stage" }
] as const

export interface DiskWatermark {
	key: (typeof WATERMARKS)[number]["key"]
	label: string
	/** Used % of this disk. */
	pct: number
	/** In bytes on this disk: null without the disk's total. */
	bytes: number | null
	/** Days until reached: 0 already there, null not forecast. */
	days: number | null
}

export interface DiskForecastView {
	node: string
	usedGb: number | null
	totalGb: number | null
	usedPct: number | null
	/** GB per day. */
	slope: number | null
	watermarks: DiskWatermark[]
	figures: Figure[]
}

/** `disk_forecast`'s evidence: the node, its disk, the slope and the watermarks (as used % of this disk). */
export function diskForecastView(evidence: Evidence | null | undefined): DiskForecastView | null {
	if (!evidence) return null
	const node = str(evidence.node)
	if (node === null) return null
	const usedGb = num(evidence.used_gb)
	const totalGb = num(evidence.total_gb)
	const slope = num(evidence.slope_gb_per_day)
	if (usedGb === null && slope === null) return null
	const thresholds = obj(evidence.thresholds_used_pct)
	const watermarks: DiskWatermark[] = []
	for (const { key, label } of WATERMARKS) {
		const pct = num(thresholds?.[key])
		if (pct === null) continue
		watermarks.push({
			key,
			label,
			pct,
			bytes: totalGb !== null && totalGb > 0 ? (pct / 100) * totalGb * GIB : null,
			days: num(evidence[`days_to_${key}`])
		})
	}
	return {
		node,
		usedGb,
		totalGb,
		usedPct: num(evidence.used_pct),
		slope,
		watermarks,
		figures: figures(evidence, [
			["samples", "Days sampled", "count"],
			["window_days", "Series spans", "days"],
			["series_since", "Series since", "time"],
			["over_high_watermark", "Over the high watermark", "bool"],
			["at_flood_stage", "At the flood stage", "bool"],
			["threshold_enabled", "Disk thresholds on", "bool"]
		])
	}
}

/** The runs read for the chart: the job's newest 30 (its daily runs over the series' window). */
export const DISK_RUNS_LIMIT = 30

/**
 * The node's used disk from `disk_forecast`'s runs (`detail.nodes[node]`, bytes): one point per UTC day,
 * the latest of each day, oldest first. A run is placed at its `detail.tick`, else its own tick, else
 * when it finished; a run without the node, or with sizes that don't parse, is left out.
 */
export function diskPoints(runs: TalonOpsRun[] | null | undefined, node: string): DiskPoint[] {
	const byDay = new Map<string, DiskPoint>()
	for (const run of runs ?? []) {
		if (run.job !== "disk_forecast") continue
		const detail = obj(run.detail)
		const row = obj(obj(detail?.nodes)?.[node])
		const used = num(row?.used)
		const total = num(row?.total)
		if (used === null || total === null || used < 0 || total <= 0 || used > total) continue
		const t = isoMs(detail?.tick) ?? isoMs(run.tick) ?? isoMs(run.finished_at)
		if (t === null) continue
		const day = new Date(t).toISOString().slice(0, 10)
		const kept = byDay.get(day)
		if (!kept || t > kept.t) byDay.set(day, { t, used, total })
	}
	return [...byDay.values()].sort((a, b) => a.t - b.t)
}

/**
 * How far the projection reaches, in days: the job's `horizon_days` setting; without it, the furthest
 * watermark the evidence forecasts. Null: no projection.
 */
export function projectionDays(settings: Record<string, unknown> | null | undefined, view: DiskForecastView): number | null {
	const horizon = num(settings?.horizon_days)
	if (horizon !== null && horizon > 0) return Math.min(horizon, 365)
	const days = view.watermarks.map(w => w.days).filter((d): d is number => d !== null && d > 0)
	return days.length ? Math.min(Math.max(...days), 365) : null
}

// ── which view ────────────────────────────────────────────────────────────────

export type ViewKind =
	| "disk_forecast"
	| "agent_hygiene"
	| "quiet_endpoints"
	| "mapping_drift"
	| "storage_usage"
	| "noisy_events"
	| "exclusion_candidates"
	| "figures"

/** The view a finding's evidence gets, by its job, or null when its evidence doesn't parse (the list then). */
export function viewKind(finding: { job: string; kind: string; evidence: Evidence | null }): ViewKind | null {
	const evidence = finding.evidence
	switch (finding.job) {
		case "disk_forecast":
			return diskForecastView(evidence) ? "disk_forecast" : null
		case "agent_hygiene":
			return agentHygieneView(evidence, finding.kind) ? "agent_hygiene" : null
		case "quiet_endpoints":
			return quietEndpointsView(evidence) ? "quiet_endpoints" : null
		case "mapping_drift":
			return mappingDriftView(evidence, finding.kind) ? "mapping_drift" : null
		case "storage_usage":
			return storageUsageView(evidence) ? "storage_usage" : null
		case "noisy_events":
			return noisyEventsView(evidence) ? "noisy_events" : null
		case "exclusion_candidates":
			return exclusionView(evidence) ? "exclusion_candidates" : null
		case "cluster_health":
			return figures(evidence, CLUSTER_HEALTH_FIGURES).length ? "figures" : null
		case "silent_log_sources":
			return figures(evidence, SILENT_LOG_SOURCES_FIGURES).length ? "figures" : null
		default:
			return null
	}
}

/** The key figures of a job shown as figures only. */
export function figureSpecs(job: string): FigureSpec[] {
	return job === "cluster_health" ? CLUSTER_HEALTH_FIGURES : job === "silent_log_sources" ? SILENT_LOG_SOURCES_FIGURES : []
}
