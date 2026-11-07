/**
 * What SOC analysts record about a customer (talon-analyst D98). Mirrors
 * `backend/app/customer_knowledge/schema/customer_knowledge.py`: each kind's `value` is a model
 * with `extra="forbid"`, so a key that isn't here is refused.
 */

export type KnowledgeKind =
	| "network_zone"
	| "public_range"
	| "asset_role"
	| "expected_activity"
	| "own_domain"
	| "identity_tenant"
	| "account_role"

export type KnowledgeZone = "server" | "workstation" | "dmz" | "guest" | "ot" | "vpn" | "cloud" | "management" | "other"

export type KnowledgePublicUse = "egress" | "hosted" | "other"

export type KnowledgeRole =
	| "domain_controller"
	| "file_server"
	| "database"
	| "web_server"
	| "mail_server"
	| "backup"
	| "hypervisor"
	| "jump_host"
	| "security_tool"
	| "workstation"
	| "other"

export type KnowledgeExpected = "scanner" | "rmm" | "pentest" | "change_window" | "other"

export type KnowledgeDomainUse = "email" | "web" | "ad" | "upn" | "other"

export type KnowledgeTenantProvider = "entra" | "google" | "other"

export type KnowledgeAccountRole = "vip" | "executive" | "admin" | "service" | "break_glass" | "shared" | "other"

export interface NetworkZoneValue {
	cidr: string
	zone: KnowledgeZone
}

export interface PublicRangeValue {
	cidr: string
	use: KnowledgePublicUse
}

export interface AssetRoleValue {
	host: string
	role: KnowledgeRole
	crown_jewel: boolean
	owner: string | null
}

export interface ExpectedActivityValue {
	what: KnowledgeExpected
	hosts: string[]
	source_cidrs: string[]
	accounts: string[]
	starts_at: string
}

/** A domain the customer owns (plan K1-7). Stored lower case and IDNA (punycode) encoded. */
export interface OwnDomainValue {
	domain: string
	uses: KnowledgeDomainUse[]
}

/** The customer's identity tenant: an Entra tenant id (a GUID) or a Google Workspace customer id. */
export interface IdentityTenantValue {
	provider: KnowledgeTenantProvider
	tenant_id: string
	name: string | null
}

/** What an account is. An identifier (`jsmith`, `CORP\jsmith`, `jsmith@corp.com`), never a display name. */
export interface AccountRoleValue {
	account: string
	role: KnowledgeAccountRole
	aliases: string[]
}

export interface KnowledgeValues {
	network_zone: NetworkZoneValue
	public_range: PublicRangeValue
	asset_role: AssetRoleValue
	expected_activity: ExpectedActivityValue
	own_domain: OwnDomainValue
	identity_tenant: IdentityTenantValue
	account_role: AccountRoleValue
}

interface KnowledgeItemFields {
	id: number
	customer_code: string
	branch: string
	note: string | null
	status: string
	source: string
	version: number
	expires_at: string | null
	expired: boolean
	created_at: string | null
	updated_at: string | null
	updated_by_username: string | null
}

/** A stored fact. */
export type KnowledgeItem = {
	[K in KnowledgeKind]: KnowledgeItemFields & { kind: K; value: KnowledgeValues[K] }
}[KnowledgeKind]

/** A fact to save. Null clears the note or the expiry. */
export type KnowledgeItemBody = {
	[K in KnowledgeKind]: { kind: K; value: KnowledgeValues[K]; note: string | null; expires_at: string | null }
}[KnowledgeKind]

/** A change to a fact: the same body, plus the `version` of the fact the analyst opened. */
export type KnowledgeItemUpdate = KnowledgeItemBody & { expected_version: number }

// ── What Talon sees ───────────────────────────────────────────────────────────

/**
 * What talon-analyst has measured of a customer's log sources (its daily `source_profile` job),
 * relayed by `GET /api/talon/knowledge/{customer_code}`. Mirrors
 * `backend/app/connectors/talon/schema/talon_knowledge.py`. Read-only: none of it is typed by a person.
 */
export type TalonSeesStatus = "ok" | "no_sources" | "no_profile" | "no_tenant_map"

export type TalonSeesCategory = "endpoint" | "identity" | "email" | "network" | "cloud" | "waf"

export type TalonSeesRole =
	| "src_ip"
	| "dst_ip"
	| "user"
	| "host"
	| "process"
	| "command_line"
	| "file_hash"
	| "file_path"
	| "url"
	| "domain"
	| "email"
	| "action"

/** A category in none of these: a verified source of it wasn't measured, so nothing is claimed. */
export interface TalonSeesCoverage {
	available: TalonSeesCategory[]
	degraded: TalonSeesCategory[]
	unavailable: TalonSeesCategory[]
}

export interface TalonSeesSource {
	pattern: string
	categories: TalonSeesCategory[]
	/** Over the last `event_days`. */
	events: number | null
	/** The source went quiet. */
	degraded: boolean | null
	measured_at: string | null
	/** Over the last `field_days`. */
	fields: Partial<Record<TalonSeesRole, string[]>>
}

/** Only `ok` carries measurements, and even then the times and windows may be null. */
export interface TalonSees {
	success: boolean
	customer_code: string
	status: TalonSeesStatus
	measured_at: string | null
	field_days: number | null
	event_days: number | null
	coverage: TalonSeesCoverage | null
	sources: TalonSeesSource[]
	not_measured: string[]
}
