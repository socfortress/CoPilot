import type { TalonPortalReviewMessagesPage, TalonPortalReviewThreadPage } from "@/types/talonPortalReview"
import { HttpClient } from "../http-client"

/**
 * The SOC's read-only review of a customer's Talon portal chats (talon-analyst D97, FR-API-43 and
 * -44), through CoPilot's `/api/talon/v2/portal_review/...`. Admins, and analysts and responders
 * with the customer and unrestricted tag access; anyone else gets `{detail, code: "review_forbidden"}`
 * (403) on the list and `thread_not_found` (404) on a transcript. Every read is audited by
 * talon-analyst. Both routes answer 404 `{"detail": "Not Found"}` while "Talon v2" is off.
 */
export default {
	listThreads(
		customerCode: string,
		query: { status?: "active" | "archived" | "all"; limit?: number; cursor?: string | null } = {},
		signal?: AbortSignal
	) {
		const params: Record<string, string | number> = { customer_code: customerCode }
		if (query.status) params.status = query.status
		if (query.limit) params.limit = query.limit
		if (query.cursor) params.cursor = query.cursor
		return HttpClient.get<TalonPortalReviewThreadPage>(`/talon/v2/portal_review/threads`, { params, signal })
	},
	getMessages(threadId: string, query: { limit?: number; before?: string | null } = {}, signal?: AbortSignal) {
		const params: Record<string, string | number> = {}
		if (query.limit) params.limit = query.limit
		if (query.before) params.before = query.before
		return HttpClient.get<TalonPortalReviewMessagesPage>(
			`/talon/v2/portal_review/threads/${encodeURIComponent(threadId)}/messages`,
			{ params, signal }
		)
	}
}
