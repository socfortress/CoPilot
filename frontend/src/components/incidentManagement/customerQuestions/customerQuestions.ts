import type { SocRequest, SocRequestUrgency } from "@/types/soc-requests"

/**
 * Pure presentation of customer questions (#1305): a Customer Portal user's question about an
 * alert or a case, open until the SOC answers it. Kept out of the components so it is testable.
 */

export type QuestionEntity = "alert" | "case"

export const URGENCY_LABELS: Record<SocRequestUrgency, string> = { low: "Low", normal: "Normal", high: "High" }

/** Naive-ui tag types: high stands out, low recedes. */
export const URGENCY_TAG: Record<SocRequestUrgency, "error" | "warning" | "default"> = {
	high: "error",
	normal: "warning",
	low: "default"
}

/** Where a question is filed: its case, else the alert the customer kept it on. */
export function questionTarget(request: SocRequest): { entity: QuestionEntity; id: number } | null {
	if (request.case_id) return { entity: "case", id: request.case_id }
	if (request.alert_id) return { entity: "alert", id: request.alert_id }
	return null
}

/** "Case #12 · Brute force" / "Alert #3". */
export function targetLabel(request: SocRequest): string {
	const target = questionTarget(request)
	if (!target) return "Removed"
	const kind = target.entity === "case" ? "Case" : "Alert"
	return `${kind} #${target.id}${request.title ? ` · ${request.title}` : ""}`
}

/** Open questions on one alert or case, from a list of open ones. */
export function openCount(requests: SocRequest[], entity: QuestionEntity, id: number): number {
	return requests.filter(r => {
		if (r.status !== "open") return false
		const target = questionTarget(r)
		return !!target && target.entity === entity && target.id === id
	}).length
}

/** How an answered question was answered, for the SOC. */
export function answeredText(request: SocRequest): string {
	if (request.status !== "answered") return ""
	const by = request.answered_by ? ` by ${request.answered_by}` : ""
	return request.answered_via === "manual" ? `Marked answered${by}` : `Answered in a comment${by}`
}
