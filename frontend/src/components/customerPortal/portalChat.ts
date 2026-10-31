import type { TalonV2UIMessage } from "@/types/talonV2"

/**
 * Talon chat in the Customer Portal (talon-analyst D97): the admin form's rules, and how the SOC's
 * read-only transcript view describes what talon-analyst sends back. Pure, so both test without a DOM.
 */

export const LIMIT_MIN = 1
export const LIMIT_MAX = 100_000
/** The form's proposals for a customer switched on for the first time; editable. */
export const PROPOSED_DAILY = 200
export const PROPOSED_PER_USER = 50

export interface PortalChatForm {
	enabled: boolean
	logSearch: boolean
	daily: number | null
	perUser: number | null
}

/** The texts the backend answers too (`talon_chat.py`), so a refusal reads the same either way. */
export const PROBLEMS = {
	range: `Daily message limits are whole numbers from ${LIMIT_MIN} to ${LIMIT_MAX.toLocaleString("en-US")}.`,
	perUserWithoutDaily: "Set the customer's daily message limit before a per-user limit.",
	perUserOverDaily: "The per-user daily message limit can't be more than the customer's.",
	needsAiReports: "Portal chat can only be turned on while the customer's AI reports are on.",
	needsDaily: "Portal chat can only be turned on with a daily message limit for the customer."
} as const

function validLimit(value: number | null): boolean {
	return value === null || (Number.isInteger(value) && value >= LIMIT_MIN && value <= LIMIT_MAX)
}

/** Why the form can't be saved, or null. */
export function formProblem(form: PortalChatForm, aiReportsEnabled: boolean): string | null {
	if (!validLimit(form.daily) || !validLimit(form.perUser)) return PROBLEMS.range
	if (form.perUser !== null && form.daily === null) return PROBLEMS.perUserWithoutDaily
	if (form.perUser !== null && form.daily !== null && form.perUser > form.daily) return PROBLEMS.perUserOverDaily
	if (form.enabled && !aiReportsEnabled) return PROBLEMS.needsAiReports
	if (form.enabled && form.daily === null) return PROBLEMS.needsDaily
	return null
}

// ── the transcript ────────────────────────────────────────────────────────────

/** One line of a turn as the review shows it: plain text, never HTML. */
export type ReviewLine =
	| { kind: "text"; text: string }
	| { kind: "checked"; text: string }
	| { kind: "draft"; text: string }
	| { kind: "offer"; text: string }
	| { kind: "tool"; text: string }

const CHECKED_KINDS: Record<string, [string, string]> = {
	alert: ["the alert", "alerts"],
	alert_list: ["an alert list", "alert lists"],
	report: ["an AI report", "AI reports"],
	assets: ["the assets", "asset lists"],
	event_search: ["an event search", "event searches"],
	event: ["an event", "events"],
	intel: ["a threat-intel lookup", "threat-intel lookups"],
	earlier_result: ["an earlier result", "earlier results"],
	soc_draft: ["a SOC draft", "SOC drafts"],
	analysis_offer: ["an AI analysis offer", "AI analysis offers"]
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value)
}

function shortText(value: unknown, max = 120): string | null {
	if (typeof value !== "string" && typeof value !== "number") return null
	const text = String(value)
	return text.length > max ? `${text.slice(0, max)}…` : text
}

/** "Checked: the alert, 2 event searches, 1 threat-intel lookup (ip)". Unknown kinds by their name. */
export function checkedSummary(data: unknown): string | null {
	const items = isRecord(data) && Array.isArray(data.items) ? data.items : null
	if (!items?.length) return null
	const parts: string[] = []
	for (const item of items) {
		if (!isRecord(item)) continue
		const kind = shortText(item.kind, 40)
		const count = typeof item.count === "number" && Number.isFinite(item.count) ? item.count : 1
		if (!kind) continue
		const [one, many] = CHECKED_KINDS[kind] ?? [kind, kind]
		const type = shortText(item.type, 40)
		const label = count === 1 ? one : `${count} ${many}`
		parts.push(type ? `${label} (${type})` : label)
	}
	return parts.length ? `Checked: ${parts.join(", ")}` : null
}

/** A read-back part as a line, or null for one the review doesn't show. */
export function describePart(part: unknown): ReviewLine | null {
	if (!isRecord(part) || typeof part.type !== "string") return null
	const type = part.type
	if (type === "text") {
		return typeof part.text === "string" && part.text.trim() ? { kind: "text", text: part.text } : null
	}
	if (type === "data-checked") {
		const text = checkedSummary(part.data)
		return text ? { kind: "checked", text } : null
	}
	if (type === "data-soc-draft") {
		const data = isRecord(part.data) ? part.data : {}
		const id = shortText(data.id, 64)
		const status = shortText(data.status, 32)
		if (!id) return null
		return { kind: "draft", text: `Drafted a question for the SOC (${id})${status ? `: ${status}` : ""}` }
	}
	if (type === "data-ai-analysis-offer") {
		const data = isRecord(part.data) ? part.data : {}
		const alert = shortText(data.alert_id, 20)
		return { kind: "offer", text: alert ? `Offered an AI analysis of alert ${alert}` : "Offered an AI analysis" }
	}
	if (type.startsWith("tool-")) {
		const name = shortText(type.slice("tool-".length), 64) || "tool"
		const state = shortText(part.state, 32)
		return { kind: "tool", text: state ? `${name} (${state})` : name }
	}
	return null
}

export interface ReviewTurn {
	id: string
	who: "customer" | "talon" | "other"
	createdAt: string | null
	status: string | null
	errorText: string | null
	feedback: string | null
	lines: ReviewLine[]
}

/** The read-back's messages as the review shows them, in order. */
export function reviewTurns(messages: TalonV2UIMessage[]): ReviewTurn[] {
	return messages.map((message, index) => {
		const metadata = isRecord(message.metadata) ? (message.metadata as Record<string, unknown>) : {}
		const feedback = shortText(metadata.feedback, 8)
		return {
			id: typeof message.id === "string" ? message.id : String(index),
			who: message.role === "user" ? "customer" : message.role === "assistant" ? "talon" : "other",
			createdAt: shortText(metadata.created_at, 40),
			status: shortText(metadata.status, 16),
			errorText: shortText(metadata.error_text, 300),
			feedback: feedback === "up" || feedback === "down" ? feedback : null,
			lines: (Array.isArray(message.parts) ? message.parts : [])
				.map(describePart)
				.filter((line): line is ReviewLine => line !== null)
		}
	})
}
