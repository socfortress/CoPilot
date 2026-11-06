import type { KnowledgeItem, KnowledgeItemBody, KnowledgeItemUpdate, TalonSees } from "@/types/customer-knowledge"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

// What SOC analysts record about a customer (talon-analyst D98). A refusal is a 422 whose text is
// written for the user; `warnings` on a save aren't refusals. A 409 on `update` means the fact changed
// after the analyst opened it.
const base = (customerCode: string) => `/customers/${encodeURIComponent(customerCode)}/knowledge`

type SavedFact = FlaskBaseResponse & { item: KnowledgeItem; warnings: string[] }

export default {
	list(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { customer_code: string; items: KnowledgeItem[] }>(base(customerCode), {
			signal
		})
	},
	create(customerCode: string, body: KnowledgeItemBody) {
		return HttpClient.post<SavedFact>(base(customerCode), body)
	},
	/** A fact keeps its kind. */
	update(customerCode: string, itemId: number, body: KnowledgeItemUpdate) {
		return HttpClient.put<SavedFact>(`${base(customerCode)}/${itemId}`, body)
	},
	remove(customerCode: string, itemId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`${base(customerCode)}/${itemId}`)
	},
	/**
	 * What talon-analyst has measured of the customer's log sources: not the facts above. A refusal is
	 * `{"detail", "code"}` (`memoryFailure` reads it), and the route is a 404 while "Talon v2" is off.
	 */
	whatTalonSees(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<TalonSees>(`/talon/knowledge/${encodeURIComponent(customerCode)}`, { signal })
	}
}
