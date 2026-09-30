import type { FlaskBaseResponse } from "@/types/flask"
import type {
	UbaAlert,
	UbaAlertUpdate,
	UbaAvailability,
	UbaEntitiesQuery,
	UbaEntityDetail,
	UbaEntitySummary,
	UbaFeedbackPayload,
	UbaPage,
	UbaRuleStat,
	UbaSignal,
	UbaSuppression,
	UbaSuppressionPayload,
	UbaTenantStatus
} from "@/types/uba"
import { HttpClient } from "../http-client"

// SOCFortress UBA through /api/uba. Upstream failures come back as 502/404/409/422 with a `reason`,
// never 401/403, so they surface as ordinary errors rather than a session logout.
const base = (customerCode: string) => `/uba/${encodeURIComponent(customerCode)}`

export default {
	/** Whether the UBA connector is configured and verified. Reads the connector row only. */
	getAvailability() {
		return HttpClient.get<FlaskBaseResponse & UbaAvailability>(`/uba/availability`, { keepOnNavigation: true })
	},
	getStatus(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { version: string; status: UbaTenantStatus | null }>(
			`${base(customerCode)}/status`,
			{ signal }
		)
	},
	getEntities(customerCode: string, query: UbaEntitiesQuery = {}, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & UbaPage & { entities: UbaEntitySummary[] }>(
			`${base(customerCode)}/entities`,
			{ params: query, signal }
		)
	},
	getEntity(customerCode: string, entityKey: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & UbaEntityDetail>(`${base(customerCode)}/entity`, {
			params: { entity_key: entityKey },
			signal
		})
	},
	getEntityTimeline(customerCode: string, entityKey: string, page = 1, pageSize = 50, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & UbaPage & { signals: UbaSignal[] }>(`${base(customerCode)}/entity/timeline`, {
			params: { entity_key: entityKey, page, page_size: pageSize },
			signal
		})
	},
	getAlerts(customerCode: string, query: { status?: "open" | "closed" | null; page?: number; page_size?: number } = {}, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & UbaPage & { alerts: UbaAlert[] }>(`${base(customerCode)}/alerts`, {
			params: query,
			signal
		})
	},
	getAlert(customerCode: string, alertId: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { alert: UbaAlert; signals: UbaSignal[]; updates: UbaAlertUpdate[] }>(
			`${base(customerCode)}/alerts/${encodeURIComponent(alertId)}`,
			{ signal }
		)
	},
	/** FALSE_POSITIVE with suppress suppresses the alert's rules for the entity (UBA records who). */
	submitFeedback(customerCode: string, alertId: string, payload: UbaFeedbackPayload) {
		return HttpClient.post<FlaskBaseResponse & { verdict: string; suppressed_rules: string[]; suppressed_until: string | null }>(
			`${base(customerCode)}/alerts/${encodeURIComponent(alertId)}/feedback`,
			payload
		)
	},
	getSuppressions(customerCode: string, query: { entity_key?: string; include_expired?: boolean } = {}, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { suppressions: UbaSuppression[] }>(`${base(customerCode)}/suppressions`, {
			params: query,
			signal
		})
	},
	addSuppressions(customerCode: string, payload: UbaSuppressionPayload) {
		return HttpClient.post<FlaskBaseResponse & { suppressions: UbaSuppression[] }>(`${base(customerCode)}/suppressions`, payload)
	},
	removeSuppressions(customerCode: string, entityKey: string, ruleId?: string | null) {
		return HttpClient.delete<FlaskBaseResponse & { removed: number }>(`${base(customerCode)}/suppressions`, {
			params: { entity_key: entityKey, rule_id: ruleId ?? undefined }
		})
	},
	getRuleStats(customerCode: string, since = "24h", signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { since: string; rules: UbaRuleStat[] }>(`${base(customerCode)}/rules/stats`, {
			params: { since },
			signal
		})
	}
}
