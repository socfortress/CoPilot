import type { FormItemRule, FormRules } from "naive-ui"
import type {
	KnowledgeExpected,
	KnowledgeItem,
	KnowledgeItemBody,
	KnowledgeKind,
	KnowledgePublicUse,
	KnowledgeRole,
	KnowledgeZone
} from "@/types/customer-knowledge"
import isIP from "validator/es/lib/isIP"
import isIPRange from "validator/es/lib/isIPRange"

/**
 * What SOC analysts record about a customer (talon-analyst D98): the words, the form's rules and
 * the request body. Pure, so all of it tests without a DOM.
 *
 * The backend has the last word. Only it can tell a public range from a private one, or spot
 * multicast, loopback and the like, so "too wide", "not public" and "unusable" stay its refusals,
 * and the form shows them.
 */

/** The backend's limits (`app/customer_knowledge`). */
export const NOTE_MAX = 200
export const NAME_MAX = 255
export const CIDR_MAX = 64
export const LIST_MAX = 50
export const EXPECTED_MAX_DAYS = 90

const DAY_MS = 86_400_000

// ── the words ─────────────────────────────────────────────────────────────────

export const CONTEXT_LINE =
	"talon-analyst reads these facts as context when it looks at this customer's alerts. They never lower a severity on their own."

export interface KindWords {
	title: string
	noun: string
	icon: string
	/** What the block is for, for someone who hasn't used it. */
	about: string
}

export const KINDS: KnowledgeKind[] = ["network_zone", "public_range", "asset_role", "expected_activity"]

export const KIND_WORDS: Record<KnowledgeKind, KindWords> = {
	network_zone: {
		title: "Network zones",
		noun: "network zone",
		icon: "carbon:network-3",
		about: "The customer's own ranges and what each one is for, so an address in an alert has a place."
	},
	public_range: {
		title: "Public ranges",
		noun: "public range",
		icon: "carbon:earth",
		about: "Public address space the customer owns. It says where traffic comes from, not that it can be trusted."
	},
	asset_role: {
		title: "Asset roles",
		noun: "asset role",
		icon: "carbon:bare-metal-server",
		about: "What a host is for, who owns it, and whether it's a crown jewel."
	},
	expected_activity: {
		title: "Expected activity",
		noun: "expected activity",
		icon: "carbon:calendar",
		about: "Work the SOC knows about, such as a pentest or a scanner: where it runs, and from when to when."
	}
}

const ZONE_LABELS: Record<KnowledgeZone, string> = {
	server: "Server",
	workstation: "Workstation",
	dmz: "DMZ",
	guest: "Guest",
	ot: "OT",
	vpn: "VPN",
	cloud: "Cloud",
	management: "Management",
	other: "Other"
}

const USE_LABELS: Record<KnowledgePublicUse, string> = {
	egress: "Egress",
	hosted: "Hosted services",
	other: "Other"
}

const ROLE_LABELS: Record<KnowledgeRole, string> = {
	domain_controller: "Domain controller",
	file_server: "File server",
	database: "Database",
	web_server: "Web server",
	mail_server: "Mail server",
	backup: "Backup",
	hypervisor: "Hypervisor",
	jump_host: "Jump host",
	security_tool: "Security tool",
	workstation: "Workstation",
	other: "Other"
}

const EXPECTED_LABELS: Record<KnowledgeExpected, string> = {
	scanner: "Scanner",
	rmm: "RMM",
	pentest: "Pentest",
	change_window: "Change window",
	other: "Other"
}

function options<T extends string>(labels: Record<T, string>): { label: string; value: T }[] {
	return (Object.keys(labels) as T[]).map(value => ({ label: labels[value], value }))
}

export const ZONE_OPTIONS = options(ZONE_LABELS)
export const USE_OPTIONS = options(USE_LABELS)
export const ROLE_OPTIONS = options(ROLE_LABELS)
export const EXPECTED_OPTIONS = options(EXPECTED_LABELS)

/** A label for a stored value; one this page doesn't know yet reads as itself. */
function worded(labels: Record<string, string>, value: string): string {
	return labels[value] ?? value
}

// ── the form ──────────────────────────────────────────────────────────────────

/** Every kind's fields, flat: the form shows the ones its kind has. Times are epoch milliseconds. */
export interface KnowledgeForm {
	kind: KnowledgeKind
	cidr: string
	zone: KnowledgeZone | null
	use: KnowledgePublicUse | null
	host: string
	role: KnowledgeRole | null
	crownJewel: boolean
	owner: string
	what: KnowledgeExpected | null
	hosts: string[]
	sourceCidrs: string[]
	accounts: string[]
	startsAt: number | null
	expiresAt: number | null
	note: string
}

export function emptyForm(kind: KnowledgeKind): KnowledgeForm {
	return {
		kind,
		cidr: "",
		zone: null,
		use: null,
		host: "",
		role: null,
		crownJewel: false,
		owner: "",
		what: null,
		hosts: [],
		sourceCidrs: [],
		accounts: [],
		startsAt: null,
		expiresAt: null,
		note: ""
	}
}

function stamp(moment: string | null): number | null {
	const time = moment ? Date.parse(moment) : Number.NaN
	return Number.isNaN(time) ? null : time
}

export function formFromItem(item: KnowledgeItem): KnowledgeForm {
	const form: KnowledgeForm = {
		...emptyForm(item.kind),
		note: item.note ?? "",
		expiresAt: stamp(item.expires_at)
	}
	switch (item.kind) {
		case "network_zone":
			return { ...form, cidr: item.value.cidr, zone: item.value.zone }
		case "public_range":
			return { ...form, cidr: item.value.cidr, use: item.value.use }
		case "asset_role":
			return {
				...form,
				host: item.value.host,
				role: item.value.role,
				crownJewel: item.value.crown_jewel,
				owner: item.value.owner ?? ""
			}
		case "expected_activity":
			return {
				...form,
				what: item.value.what,
				hosts: [...item.value.hosts],
				sourceCidrs: [...item.value.source_cidrs],
				accounts: [...item.value.accounts],
				startsAt: stamp(item.value.starts_at)
			}
	}
}

function filled(values: string[]): string[] {
	return values.map(value => value.trim()).filter(Boolean)
}

function iso(time: number | null): string | null {
	return time === null ? null : new Date(time).toISOString()
}

/**
 * The request body, for POST and PUT alike (a PUT adds `expected_version`). Null is sent on purpose:
 * an edit that clears the note or the expiry has to say so. Only call it on a form that passed its rules.
 */
export function buildBody(form: KnowledgeForm): KnowledgeItemBody {
	const common = { note: form.note.trim() || null, expires_at: iso(form.expiresAt) }
	switch (form.kind) {
		case "network_zone":
			return { ...common, kind: "network_zone", value: { cidr: form.cidr.trim(), zone: form.zone as KnowledgeZone } }
		case "public_range":
			return {
				...common,
				kind: "public_range",
				value: { cidr: form.cidr.trim(), use: form.use as KnowledgePublicUse }
			}
		case "asset_role":
			return {
				...common,
				kind: "asset_role",
				value: {
					host: form.host.trim(),
					role: form.role as KnowledgeRole,
					crown_jewel: form.crownJewel,
					owner: form.owner.trim() || null
				}
			}
		case "expected_activity":
			return {
				...common,
				kind: "expected_activity",
				value: {
					what: form.what as KnowledgeExpected,
					hosts: filled(form.hosts),
					source_cidrs: filled(form.sourceCidrs),
					accounts: filled(form.accounts),
					starts_at: iso(form.startsAt) as string
				}
			}
	}
}

// ── the rules ─────────────────────────────────────────────────────────────────

/** The texts the backend answers too (`customer_knowledge.py`), so a refusal reads the same either way. */
export const PROBLEMS = {
	cidr: "Enter an IP address or a CIDR range",
	host: "Host names can't hold spaces, wildcards, angle brackets or control characters",
	account: "Account names can't hold wildcards, angle brackets or control characters",
	text: "Notes and owners can't hold angle brackets or control characters",
	needsTarget: "Expected activity needs at least one host or source range",
	needsExpiry: "Expected activity needs an expiry",
	expiryPast: "The expiry is in the past",
	expiryTooFar: `Expected activity can't run for more than ${EXPECTED_MAX_DAYS} days from now`,
	expiryBeforeStart: "The expiry is before the start",
	startTooOld: `The start can't be more than ${EXPECTED_MAX_DAYS} days ago`,
	windowTooLong: `Expected activity can't run for more than ${EXPECTED_MAX_DAYS} days`
} as const

/** A backend refusal, worded as the form's own problems are: its fixed texts start in lower case. */
export function refusalText(text: string): string {
	return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Control and invisible characters, and angle brackets: refused in names, notes and owners. */
const UNSAFE = /[\p{Cc}\p{Cf}\p{Cs}\p{Co}\p{Zl}\p{Zp}<>]/u
const WILDCARD = /[*%]/
const WHITESPACE = /\s/
const WHITESPACE_RUN = /\s+/g
/** Any whitespace but an ordinary space. */
const ODD_WHITESPACE = /[^\S ]/

export function cidrProblem(value: string): string | null {
	const text = value.trim()
	// isIP takes an IPv6 scope id, and the backend doesn't.
	if (text.includes("%")) return PROBLEMS.cidr
	return text.length <= CIDR_MAX && (isIP(text) || isIPRange(text)) ? null : PROBLEMS.cidr
}

function nameLengthProblem(text: string): string | null {
	return text.length > NAME_MAX ? `Keep names to ${NAME_MAX} characters` : null
}

/** A host name, as the backend takes it. Blank is for the caller to judge. */
export function hostNameProblem(value: string): string | null {
	const text = value.trim()
	if (UNSAFE.test(text) || WILDCARD.test(text) || WHITESPACE.test(text)) return PROBLEMS.host
	return nameLengthProblem(text)
}

/** An account name, as the backend takes it. It may hold spaces, as in `NT AUTHORITY\SYSTEM`. */
export function accountProblem(value: string): string | null {
	const text = value.trim()
	if (UNSAFE.test(text) || WILDCARD.test(text) || ODD_WHITESPACE.test(text)) return PROBLEMS.account
	return nameLengthProblem(text)
}

export function hostProblem(value: string): string | null {
	return value.trim() ? hostNameProblem(value) : "Enter the host's name"
}

/** Free text is stored as one line, so a newline in it is fine. */
function textProblem(value: string): string | null {
	return UNSAFE.test(value.replace(WHITESPACE_RUN, " ").trim()) ? PROBLEMS.text : null
}

export function ownerProblem(value: string): string | null {
	if (value.trim().length > NAME_MAX) return `Keep the owner to ${NAME_MAX} characters`
	return textProblem(value)
}

export function noteProblem(value: string): string | null {
	if (value.trim().length > NOTE_MAX) return `Keep the note to ${NOTE_MAX} characters`
	return textProblem(value)
}

/** The first row of a list that's wrong, named, so the analyst can find it. Blank rows are dropped. */
export function listProblem(values: string[], problem: (value: string) => string | null): string | null {
	for (const value of filled(values)) {
		const text = problem(value)
		if (text) return `${value}: ${text}`
	}
	return null
}

export function targetProblem(form: KnowledgeForm): string | null {
	return filled(form.hosts).length || filled(form.sourceCidrs).length ? null : PROBLEMS.needsTarget
}

/** `kept` is the stored start: an edit may leave a time alone that would be refused as new. */
export function startProblem(startsAt: number | null, now: number, kept: number | null = null): string | null {
	if (startsAt === null) return "Expected activity needs a start"
	return startsAt !== kept && startsAt < now - EXPECTED_MAX_DAYS * DAY_MS ? PROBLEMS.startTooOld : null
}

/** `kept` is the stored expiry. The rules that read the clock only judge a time the edit moves. */
export function expiryProblem(form: KnowledgeForm, now: number, kept: number | null = null): string | null {
	const expected = form.kind === "expected_activity"
	if (form.expiresAt === null) return expected ? PROBLEMS.needsExpiry : null
	const moved = form.expiresAt !== kept
	if (moved && form.expiresAt <= now) return PROBLEMS.expiryPast
	if (!expected) return null
	const limit = EXPECTED_MAX_DAYS * DAY_MS
	if (moved && form.expiresAt > now + limit) return PROBLEMS.expiryTooFar
	if (form.startsAt === null) return null
	if (form.expiresAt <= form.startsAt) return PROBLEMS.expiryBeforeStart
	return form.expiresAt - form.startsAt > limit ? PROBLEMS.windowTooLong : null
}

const ON_INPUT = ["input", "blur"]
const ON_CHANGE = ["change", "blur"]

/** A rule from a problem. `required` only marks the field: the problem decides. */
function checked<T>(problem: (value: T) => string | null, trigger: string[], required = false): FormItemRule {
	return {
		required,
		trigger,
		validator: (_rule, value: T) => {
			const text = problem(value)
			return text ? new Error(text) : true
		}
	}
}

/**
 * Keyed by the form's fields, so a `path` is a field's name. A field only runs if its kind shows it.
 * `kept` is the opened fact as a form, on an edit.
 */
export function knowledgeRules(form: KnowledgeForm, kept: KnowledgeForm | null = null): FormRules {
	return {
		cidr: checked(cidrProblem, ON_INPUT, true),
		zone: { required: true, message: "Pick a zone", trigger: ON_CHANGE },
		use: { required: true, message: "Pick what the range is used for", trigger: ON_CHANGE },
		host: checked(hostProblem, ON_INPUT, true),
		role: { required: true, message: "Pick a role", trigger: ON_CHANGE },
		owner: checked(ownerProblem, ON_INPUT),
		what: { required: true, message: "Pick what is expected", trigger: ON_CHANGE },
		// A field for the rule that needs one of two lists: it reads both.
		hosts: checked((hosts: string[]) => listProblem(hosts, hostNameProblem) ?? targetProblem(form), ON_INPUT),
		sourceCidrs: checked((ranges: string[]) => listProblem(ranges, cidrProblem), ON_INPUT),
		accounts: checked((accounts: string[]) => listProblem(accounts, accountProblem), ON_INPUT),
		startsAt: checked(
			(startsAt: number | null) => startProblem(startsAt, Date.now(), kept?.startsAt ?? null),
			ON_CHANGE,
			true
		),
		expiresAt: checked(
			() => expiryProblem(form, Date.now(), kept?.expiresAt ?? null),
			ON_CHANGE,
			form.kind === "expected_activity"
		),
		note: checked(noteProblem, ON_INPUT)
	}
}

// ── a fact, for reading ───────────────────────────────────────────────────────

export interface FactDetail {
	label: string
	values: string[]
}

export interface FactView {
	/** The value the fact is about: a range, a host, or what is expected. */
	headline: string
	crownJewel: boolean
	details: FactDetail[]
}

function detail(label: string, values: (string | null)[]): FactDetail[] {
	const shown = values.filter((value): value is string => !!value)
	return shown.length ? [{ label, values: shown }] : []
}

/** `when` formats a time the viewer's way, which takes the settings store. */
export function factView(item: KnowledgeItem, when: (moment: string) => string): FactView {
	const expires = detail("Expires", [item.expires_at && when(item.expires_at)])
	switch (item.kind) {
		case "network_zone":
			return {
				headline: item.value.cidr,
				crownJewel: false,
				details: [...detail("Zone", [worded(ZONE_LABELS, item.value.zone)]), ...expires]
			}
		case "public_range":
			return {
				headline: item.value.cidr,
				crownJewel: false,
				details: [...detail("Use", [worded(USE_LABELS, item.value.use)]), ...expires]
			}
		case "asset_role":
			return {
				headline: item.value.host,
				crownJewel: item.value.crown_jewel,
				details: [
					...detail("Role", [worded(ROLE_LABELS, item.value.role)]),
					...detail("Owner", [item.value.owner]),
					...expires
				]
			}
		case "expected_activity":
			return {
				headline: worded(EXPECTED_LABELS, item.value.what),
				crownJewel: false,
				details: [
					...detail("Hosts", item.value.hosts),
					...detail("Source ranges", item.value.source_cidrs),
					...detail("Accounts", item.value.accounts),
					...detail("Starts", [when(item.value.starts_at)]),
					...expires
				]
			}
	}
}

export function lastChanged(item: KnowledgeItem, when: (moment: string) => string): string | null {
	const by = item.updated_by_username
	const at = item.updated_at && when(item.updated_at)
	if (by && at) return `Last changed by ${by}, ${at}`
	if (by) return `Last changed by ${by}`
	return at ? `Last changed ${at}` : null
}

export interface FactGroup extends KindWords {
	kind: KnowledgeKind
	facts: KnowledgeItem[]
}

/** The page's blocks, all four, in order. A kind this page doesn't know yet isn't shown. */
export function groupFacts(items: KnowledgeItem[]): FactGroup[] {
	return KINDS.map(kind => ({ ...KIND_WORDS[kind], kind, facts: items.filter(item => item.kind === kind) }))
}
