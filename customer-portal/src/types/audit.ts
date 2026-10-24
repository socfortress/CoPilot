import type { PortalCustomer } from "@/types/auth"

/**
 * A customer admin's audit log (#1298): `/customer_portal/audit`. Times are ISO 8601 UTC.
 *
 * The SOC is never named (`actor.kind === "soc"`), and only the customer's own users carry
 * an address; the API sends nothing more, so the page cannot show more by mistake.
 */

export type AuditCategory = "alerts" | "cases" | "reports" | "users" | "account"
export type AuditActorKind = "member" | "soc" | "other" | "unknown"
export type AuditTargetType = "alert" | "case" | "report" | "user"

export interface AuditActor {
	kind: AuditActorKind
	/** Only for one of the customer's own portal users. */
	username: string | null
}

export interface AuditTarget {
	type: AuditTargetType
	id: string
	/** A report's or a case's name, a user's username. */
	label: string | null
}

export interface AuditEntry {
	id: number
	timestamp: string
	action: string
	label: string
	category: AuditCategory
	actor: AuditActor
	customer_code: string | null
	target: AuditTarget | null
	from_value: string | null
	to_value: string | null
	result: "success" | "failure" | "unknown"
	source_ip: string | null
}

export interface AuditMember {
	id: number
	username: string
}

export interface AuditLog {
	entries: AuditEntry[]
	total: number
	page: number
	page_size: number
	/** Days the log is kept; 0 = for ever. */
	retention_days: number
	members: AuditMember[]
}

export interface AuditAvailability {
	available: boolean
	customers: PortalCustomer[]
}

/** The API's query: `since` inclusive, `until` exclusive, both ISO instants. */
export interface AuditQuery {
	category?: AuditCategory | null
	userId?: number | null
	since?: string | null
	until?: string | null
	page?: number
	pageSize?: number
}
