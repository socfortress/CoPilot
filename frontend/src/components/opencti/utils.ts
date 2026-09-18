import type { BadgeColor } from "@/components/common/Badge.vue"

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
