import type { TalonMemoryFailure } from "@/api/endpoints/talonMemory"
import type { TalonSeesCategory, TalonSeesCoverage, TalonSeesRole, TalonSeesSource } from "@/types/customer-knowledge"

/**
 * The "What Talon sees" panel: its words, labels and rows. Pure, so all of it tests without a DOM.
 *
 * Everything the panel shows is measured from the customer's logs by talon-analyst's daily job. None
 * of it is typed by a person, and it doesn't come from the facts on this page, so no word here may
 * suggest that Talon reads those facts.
 */

// ── the words ─────────────────────────────────────────────────────────────────

export const NO_PROFILE_TEXT =
	"Talon hasn't measured this customer's log sources in the last 7 days. Its source_profile job may be off."

/** The tenant map's gap, not the customer's logs: without this, every kind of log would read "None". */
export const NO_VERIFIED_SOURCES_TEXT =
	"Talon has no verified log sources for this customer, so an investigation has nothing to search. Check that its index patterns have reached Talon's tenant map."

export const NO_TENANT_MAP_TEXT =
	"Talon can't read its tenant map right now, so an investigation wouldn't see this customer's log sources either."

/** Standing alone, without the panel's heading, so it says what it is about. */
export const UNSUPPORTED_TEXT =
	"What Talon sees isn't available here: it needs Talon v2 on, and a talon-analyst with the knowledge API."

export const NOT_MEASURED_ABOUT = "Verified log sources without a recent measurement."

/** A customer without sources isn't a failure, so the list says so instead of showing nothing. */
export const NO_SOURCES_TEXT = "No log sources were measured."

const LOGS_LINE = "Measured daily from this customer's logs, not from anything recorded on this page."

const PACK_LINE = "An investigation gets a shorter list: more of the alert's own source, and a few fields of the others."

/** `when` formats a time the viewer's way, which takes the settings store. */
export function measuredLine(measuredAt: string | null, when: (moment: string) => string): string {
	return measuredAt ? `${LOGS_LINE} Last measured ${when(measuredAt)}.` : LOGS_LINE
}

/** Null when Talon didn't say how many: an unknown count isn't zero. */
export function eventsLine(events: number | null, days: number | null): string | null {
	if (events === null) return null
	const count = `${events.toLocaleString()} ${events === 1 ? "event" : "events"}`
	if (days === null) return count
	return `${count} in the last ${days === 1 ? "day" : `${days} days`}`
}

export function fieldsLine(days: number | null): string {
	if (days === null) return PACK_LINE
	return `Fields seen in the last ${days === 1 ? "day" : `${days} days`}. ${PACK_LINE}`
}

/**
 * A source the last run couldn't measure keeps its last good row, so its numbers are older than the
 * time at the top of the panel. Null when they're the run's own, or a time is missing or unreadable.
 */
export function carriedLine(
	measuredAt: string | null,
	runAt: string | null,
	when: (moment: string) => string
): string | null {
	if (!measuredAt || !runAt) return null
	return Date.parse(measuredAt) < Date.parse(runAt)
		? `The last run couldn't measure this source. These numbers are from ${when(measuredAt)}.`
		: null
}

// ── coverage ──────────────────────────────────────────────────────────────────

export const CATEGORIES: TalonSeesCategory[] = ["endpoint", "identity", "email", "network", "cloud", "waf"]

const CATEGORY_LABELS: Record<TalonSeesCategory, string> = {
	endpoint: "Endpoint",
	identity: "Identity",
	email: "Email",
	network: "Network",
	cloud: "Cloud",
	waf: "WAF"
}

export function categoryLabel(category: TalonSeesCategory): string {
	return CATEGORY_LABELS[category] ?? category
}

export type CoverageState = keyof TalonSeesCoverage | "not_measured"

/** Weakest first, so a category listed twice claims the least. */
const STATES: (keyof TalonSeesCoverage)[] = ["unavailable", "degraded", "available"]

const STATE_WORDS: Record<CoverageState, string> = {
	available: "Available",
	degraded: "Quiet",
	unavailable: "None",
	not_measured: "Not measured"
}

export interface CoverageRow {
	category: TalonSeesCategory
	label: string
	state: CoverageState
	word: string
}

/** One row per category, all six, in order. In no state: nothing is claimed about it. */
export function coverageRows(coverage: TalonSeesCoverage | null): CoverageRow[] {
	return CATEGORIES.map(category => {
		const state = STATES.find(name => coverage?.[name].includes(category)) ?? "not_measured"
		return { category, label: categoryLabel(category), state, word: STATE_WORDS[state] }
	})
}

// ── log sources ───────────────────────────────────────────────────────────────

const ROLE_LABELS: Record<TalonSeesRole, string> = {
	src_ip: "Source IP",
	dst_ip: "Destination IP",
	user: "User",
	host: "Host",
	process: "Process",
	command_line: "Command line",
	file_hash: "File hash",
	file_path: "File path",
	url: "URL",
	domain: "Domain",
	email: "Email",
	action: "Action"
}

const ROLES = Object.keys(ROLE_LABELS) as TalonSeesRole[]

export interface FieldRow {
	role: TalonSeesRole
	label: string
	names: string[]
}

export interface SourceView {
	pattern: string
	quiet: boolean
	categories: string[]
	events: string | null
	carried: string | null
	fields: FieldRow[]
}

/** In a fixed order, whatever order Talon sent. A role this page doesn't know yet isn't shown. */
export function fieldRows(fields: TalonSeesSource["fields"]): FieldRow[] {
	return ROLES.flatMap(role => {
		const names = fields[role]
		return names?.length ? [{ role, label: ROLE_LABELS[role], names }] : []
	})
}

export function sourceView(
	source: TalonSeesSource,
	eventDays: number | null,
	runAt: string | null,
	when: (moment: string) => string
): SourceView {
	return {
		pattern: source.pattern,
		quiet: source.degraded === true,
		categories: source.categories.map(categoryLabel),
		events: eventsLine(source.events, eventDays),
		carried: carriedLine(source.measured_at, runAt, when),
		fields: fieldRows(source.fields)
	}
}

// ── failures ──────────────────────────────────────────────────────────────────

/**
 * Talon can't answer this here, and nobody can fix that by trying again: an older talon-analyst, its
 * v2 API off (`unsupported`), or CoPilot's own bare 404 while "Talon v2" is off (`v2_off`).
 */
export function isUnsupported(failure: TalonMemoryFailure | null): boolean {
	return failure?.code === "unsupported" || failure?.code === "v2_off"
}
