import type { BadgeColor } from "@/components/common/Badge.vue"
import dayjs from "@/utils/dayjs"

/** OpenCTI scores run 0–100; 75 is what most feeds assign to a confirmed-malicious indicator. */
export function scoreColor(score: number | null | undefined): BadgeColor | undefined {
	if (score === null || score === undefined) return undefined
	if (score >= 75) return "danger"
	if (score >= 50) return "warning"
	return undefined
}

export function scoreTagType(score: number | null | undefined): "error" | "warning" | "default" {
	const color = scoreColor(score)
	return color === "danger" ? "error" : color === "warning" ? "warning" : "default"
}

export function markingType(marking: string): "error" | "warning" | "success" | "default" {
	const tlp = marking.toUpperCase()
	if (tlp.startsWith("TLP:RED")) return "error"
	if (tlp.startsWith("TLP:AMBER")) return "warning"
	if (tlp.startsWith("TLP:GREEN")) return "success"
	return "default"
}

/**
 * One indicator lifecycle state, so every surface renders "valid / expired /
 * revoked" with the same shape and only the colour changes. Revocation wins
 * over expiry: a revoked indicator's expiry date is moot.
 */
export type IndicatorValidity = "valid" | "expired" | "revoked" | "unknown"

export function indicatorValidity(indicator: {
	revoked: boolean | null
	valid_until: string | null
}): IndicatorValidity {
	if (indicator.revoked) return "revoked"
	if (!indicator.valid_until) return "unknown"
	return dayjs(indicator.valid_until).isBefore(dayjs()) ? "expired" : "valid"
}

export const VALIDITY_LABEL: Record<IndicatorValidity, string> = {
	valid: "valid",
	expired: "expired",
	revoked: "revoked",
	unknown: "no expiry"
}

export const VALIDITY_DOT: Record<IndicatorValidity, string> = {
	valid: "bg-success",
	expired: "bg-warning",
	revoked: "bg-error",
	unknown: "bg-border"
}
