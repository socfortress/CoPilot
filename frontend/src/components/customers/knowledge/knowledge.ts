import type { FormItemRule, FormRules } from "naive-ui"
import type {
	KnowledgeAccountRole,
	KnowledgeDomainUse,
	KnowledgeExpected,
	KnowledgeItem,
	KnowledgeItemBody,
	KnowledgeKind,
	KnowledgePublicUse,
	KnowledgeRole,
	KnowledgeTenantProvider,
	KnowledgeZone
} from "@/types/customer-knowledge"
import type { BusinessCalendar, Weekday, WorkingWindow } from "@/types/soc-management"
import isIP from "validator/es/lib/isIP"
import isIPRange from "validator/es/lib/isIPRange"
import { dayError, WEEKDAY_LABEL, WEEKDAYS } from "@/components/socManagement/policies/calendar"
import { countryName, isCountryCode } from "./countries"

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
export const DOMAIN_MAX = 253
export const TENANT_ID_MAX = 128
export const ALIASES_MAX = 10
export const TIME_ZONE_MAX = 64
export const WINDOWS_MAX = 6
export const COUNTRIES_MAX = 50

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

export const KINDS: KnowledgeKind[] = [
	"business_profile",
	"network_zone",
	"public_range",
	"asset_role",
	"expected_activity",
	"own_domain",
	"identity_tenant",
	"account_role"
]

export const KIND_WORDS: Record<KnowledgeKind, KindWords> = {
	business_profile: {
		title: "Business context",
		noun: "business context",
		icon: "carbon:time",
		about: "When and where the customer works: its time zone, business hours and the countries it operates in, so an alert's time and an address's country can be read against them."
	},
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
	},
	own_domain: {
		title: "Domains",
		noun: "domain",
		icon: "carbon:email",
		about: "The customer's own domains and what each is for, so its mail and sites stand apart from lookalikes. A subdomain counts too."
	},
	identity_tenant: {
		title: "Identity tenants",
		noun: "identity tenant",
		icon: "carbon:cloud",
		about: "The customer's Microsoft 365 (Entra) or Google Workspace tenant, so a sign-in from another tenant stands out."
	},
	account_role: {
		title: "Accounts",
		noun: "account",
		icon: "carbon:user-role",
		about: "Accounts that matter: VIPs, admins, service and break-glass accounts. Record the account's name, never a person's display name."
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

const DOMAIN_USE_LABELS: Record<KnowledgeDomainUse, string> = {
	email: "Email",
	web: "Web",
	ad: "Active Directory",
	upn: "UPN suffix",
	other: "Other"
}

const PROVIDER_LABELS: Record<KnowledgeTenantProvider, string> = {
	entra: "Microsoft Entra (Microsoft 365)",
	google: "Google Workspace",
	other: "Other"
}

const ACCOUNT_ROLE_LABELS: Record<KnowledgeAccountRole, string> = {
	vip: "VIP",
	executive: "Executive",
	admin: "Admin",
	service: "Service account",
	break_glass: "Break-glass account",
	shared: "Shared account",
	other: "Other"
}

function options<T extends string>(labels: Record<T, string>): { label: string; value: T }[] {
	return (Object.keys(labels) as T[]).map(value => ({ label: labels[value], value }))
}

export const ZONE_OPTIONS = options(ZONE_LABELS)
export const USE_OPTIONS = options(USE_LABELS)
export const ROLE_OPTIONS = options(ROLE_LABELS)
export const EXPECTED_OPTIONS = options(EXPECTED_LABELS)
export const DOMAIN_USE_OPTIONS = options(DOMAIN_USE_LABELS)
export const PROVIDER_OPTIONS = options(PROVIDER_LABELS)
export const ACCOUNT_ROLE_OPTIONS = options(ACCOUNT_ROLE_LABELS)

/** Kinds a customer has one of: their block offers "Add" only while it's empty. */
export const SINGLE_KINDS: ReadonlySet<KnowledgeKind> = new Set(["business_profile"])

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
	domain: string
	uses: KnowledgeDomainUse[]
	provider: KnowledgeTenantProvider | null
	tenantId: string
	tenantName: string
	account: string
	accountRole: KnowledgeAccountRole | null
	aliases: string[]
	timeZone: string | null
	/** Every day, closed ones empty: the shape the SLA calendar's week editor edits. */
	week: Record<Weekday, WorkingWindow[]>
	alwaysOpen: boolean
	countries: string[]
}

/** A week with every day closed. */
export function closedWeek(): Record<Weekday, WorkingWindow[]> {
	return fullWeek({})
}

/** A stored or an SLA calendar's week as the editor holds it: every day, copied, so editing leaves the source alone. */
export function fullWeek(week: Partial<Record<Weekday, WorkingWindow[]>>): Record<Weekday, WorkingWindow[]> {
	return Object.fromEntries(
		WEEKDAYS.map(day => [day, (week[day] ?? []).map(([start, end]) => [start, end] as WorkingWindow)])
	) as Record<Weekday, WorkingWindow[]>
}

/** The open days in week order, each with its windows in order: what the backend stores. */
export function openDays(week: Record<Weekday, WorkingWindow[]>): Partial<Record<Weekday, WorkingWindow[]>> {
	return Object.fromEntries(
		WEEKDAYS.filter(day => week[day].length).map(day => [
			day,
			week[day].map(([start, end]) => [start, end] as WorkingWindow).sort((a, b) => a[0].localeCompare(b[0]))
		])
	)
}

/** A customer's own SLA calendar, copied into a profile: its zone and its week, never its holidays. */
export function fromCalendar(calendar: Pick<BusinessCalendar, "timezone" | "week">): {
	timeZone: string
	week: Record<Weekday, WorkingWindow[]>
} {
	return { timeZone: calendar.timezone, week: fullWeek(calendar.week) }
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
		note: "",
		domain: "",
		uses: [],
		provider: null,
		tenantId: "",
		tenantName: "",
		account: "",
		accountRole: null,
		aliases: [],
		timeZone: null,
		week: closedWeek(),
		alwaysOpen: false,
		countries: []
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
		case "own_domain":
			return { ...form, domain: item.value.domain, uses: [...item.value.uses] }
		case "identity_tenant":
			return {
				...form,
				provider: item.value.provider,
				tenantId: item.value.tenant_id,
				tenantName: item.value.name ?? ""
			}
		case "account_role":
			return {
				...form,
				account: item.value.account,
				accountRole: item.value.role,
				aliases: [...item.value.aliases]
			}
		case "business_profile":
			return {
				...form,
				timeZone: item.value.time_zone,
				week: fullWeek(item.value.week),
				alwaysOpen: item.value.always_open,
				countries: [...item.value.countries]
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
			return {
				...common,
				kind: "network_zone",
				value: { cidr: form.cidr.trim(), zone: form.zone as KnowledgeZone }
			}
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
		case "own_domain":
			return { ...common, kind: "own_domain", value: { domain: form.domain.trim(), uses: [...form.uses] } }
		case "identity_tenant":
			return {
				...common,
				kind: "identity_tenant",
				value: {
					provider: form.provider as KnowledgeTenantProvider,
					tenant_id: form.tenantId.trim(),
					name: form.tenantName.trim() || null
				}
			}
		case "account_role":
			return {
				...common,
				kind: "account_role",
				value: {
					account: form.account.trim(),
					role: form.accountRole as KnowledgeAccountRole,
					aliases: filled(form.aliases)
				}
			}
		case "business_profile":
			return {
				...common,
				kind: "business_profile",
				value: {
					time_zone: (form.timeZone ?? "").trim(),
					// Round the clock has no hours: the switch wins over what the editor still holds.
					week: form.alwaysOpen ? {} : openDays(form.week),
					always_open: form.alwaysOpen,
					countries: [...form.countries]
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
	text: "Notes, owners and names can't hold angle brackets or control characters",
	domain: "Enter a domain name, such as example.com, without a scheme, path, port or wildcard",
	identifier: "Record the account's name, such as jsmith, CORP\\jsmith or jsmith@corp.com, not a display name",
	entraTenant: "An Entra tenant id is a GUID, such as 72f988bf-86f1-41af-91ab-2d7cd011db47",
	googleTenant: "A Google Workspace customer id starts with C, such as C01b2c3d4",
	tenant: "Enter the tenant's id as the provider shows it",
	needsTarget: "Expected activity needs at least one host or source range",
	needsExpiry: "Expected activity needs an expiry",
	expiryPast: "The expiry is in the past",
	expiryTooFar: `Expected activity can't run for more than ${EXPECTED_MAX_DAYS} days from now`,
	expiryBeforeStart: "The expiry is before the start",
	startTooOld: `The start can't be more than ${EXPECTED_MAX_DAYS} days ago`,
	windowTooLong: `Expected activity can't run for more than ${EXPECTED_MAX_DAYS} days`,
	timeZone: "Pick a time zone by its region and city, such as America/Denver",
	country: "Enter countries as two-letter ISO codes, such as US or GB"
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

/** What can't be in a domain, before the backend's IDNA encoding and its suffix and provider lists. */
const NOT_IN_A_DOMAIN = /[\s*%/@:?#\\[\]<>"'`=&;,]/
const ASCII_LABEL = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i
const NON_ASCII = /[^\u0020-\u007E]/

/**
 * A domain, as far as the form can tell. The backend encodes an international one (IDNA) and refuses
 * a shared suffix (`co.uk`, `onmicrosoft.com`) or a public mail provider's: those stay its refusals.
 */
export function domainProblem(value: string): string | null {
	const text = value.trim().replace(/\.$/, "")
	if (!text) return "Enter the domain"
	if (UNSAFE.test(text) || NOT_IN_A_DOMAIN.test(text) || isIP(text)) return PROBLEMS.domain
	const labels = text.split(".")
	if (text.length > DOMAIN_MAX || labels.length < 2) return PROBLEMS.domain
	if (labels.some(label => !label || (!NON_ASCII.test(label) && !ASCII_LABEL.test(label)))) return PROBLEMS.domain
	return /^\d+$/.test(labels[labels.length - 1]) ? PROBLEMS.domain : null
}

const GUID = /^\{?[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}\}?$/i
const GOOGLE_TENANT = /^C[0-9A-Za-z]{4,20}$/
const OTHER_TENANT = /^[0-9A-Z][\w.:-]{0,127}$/i

/** A tenant id in its provider's form. */
export function tenantIdProblem(provider: KnowledgeTenantProvider | null, value: string): string | null {
	const text = value.trim()
	if (!text) return "Enter the tenant's id"
	if (provider === "entra") return GUID.test(text) ? null : PROBLEMS.entraTenant
	if (provider === "google") return GOOGLE_TENANT.test(text) ? null : PROBLEMS.googleTenant
	return OTHER_TENANT.test(text) ? null : PROBLEMS.tenant
}

/**
 * An account identifier: an account name (`accountProblem`) that isn't a display name. `CORP\jsmith`'s
 * domain may hold spaces, as `NT AUTHORITY\SYSTEM` does; the account part never.
 */
export function identifierProblem(value: string): string | null {
	const text = value.trim()
	const name = accountProblem(text)
	if (name) return name
	if (text.includes("\\")) {
		const [domain, ...rest] = text.split("\\")
		const account = rest.join("\\")
		return !domain.trim() || !account || rest.length > 1 || WHITESPACE.test(account) ? PROBLEMS.identifier : null
	}
	if (WHITESPACE.test(text)) return PROBLEMS.identifier
	if (text.includes("@")) {
		const [local, ...domain] = text.split("@")
		return !local || domain.length !== 1 || !domain[0] ? PROBLEMS.identifier : null
	}
	return null
}

export function accountIdProblem(value: string): string | null {
	return value.trim() ? identifierProblem(value) : "Enter the account's name"
}

export function tenantNameProblem(value: string): string | null {
	if (value.trim().length > NAME_MAX) return `Keep the name to ${NAME_MAX} characters`
	return textProblem(value)
}

/**
 * An IANA zone by its region and city, or UTC: never an abbreviation (`MST`) or a fixed `Etc/` offset.
 * Whether the zone exists is the backend's call, as the browser's list can be older or newer.
 */
export function timeZoneProblem(value: string | null): string | null {
	const text = (value ?? "").trim()
	if (!text) return "Pick the customer's time zone"
	if (text.length > TIME_ZONE_MAX) return PROBLEMS.timeZone
	return text === "UTC" || (text.includes("/") && !text.startsWith("Etc/")) ? null : PROBLEMS.timeZone
}

/** The first day whose windows are wrong, named, in the SLA calendar editor's words. */
export function weekProblem(week: Record<Weekday, WorkingWindow[]>): string | null {
	for (const day of WEEKDAYS) {
		if (week[day].length > WINDOWS_MAX) return `${WEEKDAY_LABEL[day]}: keep to ${WINDOWS_MAX} windows`
		const problem = dayError(week[day])
		if (problem) return `${WEEKDAY_LABEL[day]}: ${problem.toLowerCase()}`
	}
	return null
}

export function countriesProblem(codes: string[]): string | null {
	if (codes.length > COUNTRIES_MAX) return `Keep to ${COUNTRIES_MAX} countries`
	return codes.every(isCountryCode) ? null : PROBLEMS.country
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
		note: checked(noteProblem, ON_INPUT),
		domain: checked(domainProblem, ON_INPUT, true),
		uses: checked((uses: KnowledgeDomainUse[]) => (uses.length ? null : "Pick at least one use"), ON_CHANGE, true),
		provider: { required: true, message: "Pick the provider", trigger: ON_CHANGE },
		tenantId: checked((tenantId: string) => tenantIdProblem(form.provider, tenantId), ON_INPUT, true),
		tenantName: checked(tenantNameProblem, ON_INPUT),
		account: checked(accountIdProblem, ON_INPUT, true),
		accountRole: { required: true, message: "Pick a role", trigger: ON_CHANGE },
		aliases: checked((aliases: string[]) => listProblem(aliases, identifierProblem), ON_INPUT),
		timeZone: checked(timeZoneProblem, ON_CHANGE, true),
		// The switch clears the hours when the body is built, so the editor behind it isn't judged.
		week: checked(
			(week: Record<Weekday, WorkingWindow[]>) => (form.alwaysOpen ? null : weekProblem(week)),
			ON_CHANGE
		),
		countries: checked(countriesProblem, ON_CHANGE)
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
		case "own_domain":
			return {
				headline: item.value.domain,
				crownJewel: false,
				details: [
					...detail(
						"Used for",
						item.value.uses.map(use => worded(DOMAIN_USE_LABELS, use))
					),
					...expires
				]
			}
		case "identity_tenant":
			return {
				headline: item.value.name ?? item.value.tenant_id,
				crownJewel: false,
				details: [
					...detail("Provider", [worded(PROVIDER_LABELS, item.value.provider)]),
					...detail("Tenant id", [item.value.tenant_id]),
					...expires
				]
			}
		case "account_role":
			return {
				headline: item.value.account,
				crownJewel: false,
				details: [
					...detail("Role", [worded(ACCOUNT_ROLE_LABELS, item.value.role)]),
					...detail("Also known as", item.value.aliases),
					...expires
				]
			}
		case "business_profile":
			return {
				headline: item.value.time_zone,
				crownJewel: false,
				details: [
					...detail("Hours", item.value.always_open ? ["Around the clock"] : hoursLines(item.value.week)),
					...detail(
						"Countries",
						item.value.countries.map(code => `${countryName(code)} (${code})`)
					),
					...expires
				]
			}
	}
}

/** "Mon–Fri" for a run of three days or more, else each day: "Sat, Sun". */
function dayRuns(days: Weekday[]): string {
	const short = (day: Weekday) => WEEKDAY_LABEL[day].slice(0, 3)
	const parts: string[] = []
	let index = 0
	while (index < days.length) {
		let end = index
		while (end + 1 < days.length && WEEKDAYS.indexOf(days[end + 1]) === WEEKDAYS.indexOf(days[end]) + 1) end++
		if (end - index >= 2) parts.push(`${short(days[index])}–${short(days[end])}`)
		else parts.push(...days.slice(index, end + 1).map(short))
		index = end + 1
	}
	return parts.join(", ")
}

/** A week in words, days with the same windows together: "Mon–Fri 08:00–17:00". */
export function hoursLines(week: Partial<Record<Weekday, WorkingWindow[]>>): string[] {
	const byWindows = new Map<string, Weekday[]>()
	for (const day of WEEKDAYS) {
		const windows = week[day] ?? []
		if (!windows.length) continue
		const text = windows.map(([start, end]) => `${start}–${end}`).join(", ")
		byWindows.set(text, [...(byWindows.get(text) ?? []), day])
	}
	return [...byWindows].map(([windows, days]) => `${dayRuns(days)} ${windows}`)
}

/** "Tuesday 14:05": the time at `now` in `timeZone`, or null for a zone the browser doesn't know. */
export function nowThere(timeZone: string | null, now: number): string | null {
	if (!timeZone) return null
	try {
		const parts = new Intl.DateTimeFormat("en-GB", {
			timeZone,
			weekday: "long",
			hour: "2-digit",
			minute: "2-digit",
			hourCycle: "h23"
		}).formatToParts(new Date(now))
		const part = (type: string) => parts.find(p => p.type === type)?.value ?? ""
		return `${part("weekday")} ${part("hour")}:${part("minute")}`
	} catch {
		return null
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
	/** False for a kind a customer has one of, once it has it: the SOC edits that one. */
	canAdd: boolean
}

/** The page's blocks, every kind, in order. A kind this page doesn't know yet isn't shown. */
export function groupFacts(items: KnowledgeItem[]): FactGroup[] {
	return KINDS.map(kind => {
		const facts = items.filter(item => item.kind === kind)
		return { ...KIND_WORDS[kind], kind, facts, canAdd: !SINGLE_KINDS.has(kind) || !facts.length }
	})
}
