export type AuditFilterTypes =
	"action" | "result" | "actor_username" | "entity_type" | "customer_code" | "search" | "dateRange"

export type AuditListFilterValue = string | [number, number] | null

export interface AuditListFilter {
	type: AuditFilterTypes
	value: AuditListFilterValue
}
