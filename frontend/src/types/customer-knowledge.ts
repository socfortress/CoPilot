/**
 * What SOC analysts record about a customer (talon-analyst D98). Mirrors
 * `backend/app/customer_knowledge/schema/customer_knowledge.py`: each kind's `value` is a model
 * with `extra="forbid"`, so a key that isn't here is refused.
 */

export type KnowledgeKind = "network_zone" | "public_range" | "asset_role" | "expected_activity"

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

export interface KnowledgeValues {
	network_zone: NetworkZoneValue
	public_range: PublicRangeValue
	asset_role: AssetRoleValue
	expected_activity: ExpectedActivityValue
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
