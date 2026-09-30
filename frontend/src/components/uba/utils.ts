import type { UbaFailureReason } from "@/types/uba"

/** What to do about an upstream failure (the proxy returns a `reason`, never a 401/403). */
export function reasonHint(reason: UbaFailureReason | string | null | undefined): string | null {
	switch (reason) {
		case "not_configured":
			return "Set the SOCFortress UBA connector's URL and API key under Connectors."
		case "unreachable":
			return "CoPilot can't reach the UBA API. Check the connector URL and that UBA's API is published where CoPilot's backend can reach it."
		case "key_rejected":
			return "UBA rejected the API key. Create one with `uba-admin api-keys create --name copilot --scope write` and update the connector."
		case "insufficient_scope":
			return "The UBA API key can only read. Suppressions and verdicts need a key with scope write."
		case "not_found":
			return "UBA has no such item for this customer (or the API key isn't allowed to see this customer)."
		default:
			return null
	}
}

/** Risk bands follow UBA's alerting: 100 opens an alert, 150 is high, 200 critical. */
export function riskTagType(risk: number): "error" | "warning" | "info" | "default" {
	if (risk >= 150) return "error"
	if (risk >= 100) return "warning"
	if (risk >= 30) return "info"
	return "default"
}

export function riskLabel(risk: number): string {
	return risk >= 10 ? risk.toFixed(0) : risk.toFixed(1)
}

export const ENTITY_TYPE_LABEL: Record<string, string> = {
	actor: "user",
	target: "user",
	host: "host",
	src_ip: "address",
	tenant: "tenant"
}

export function entityTypeLabel(type: string | null | undefined): string {
	return (type && ENTITY_TYPE_LABEL[type]) || type || "entity"
}

export function formatLag(seconds: number | null | undefined): string {
	if (seconds == null) return "unknown"
	if (seconds < 90) return `${Math.round(seconds)} s`
	if (seconds < 5400) return `${Math.round(seconds / 60)} min`
	return `${Math.round(seconds / 3600)} h`
}

export const FALSE_POSITIVE_REASONS = [
	{ label: "Expected activity", value: "EXPECTED_ACTIVITY" },
	{ label: "Known application", value: "KNOWN_APPLICATION" },
	{ label: "Authorized user", value: "AUTHORIZED_USER" },
	{ label: "Rule too sensitive", value: "RULE_TOO_SENSITIVE" },
	{ label: "Other", value: "OTHER" }
]
