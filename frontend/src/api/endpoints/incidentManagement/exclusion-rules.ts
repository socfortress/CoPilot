import type { FlaskBaseResponse } from "@/types/flask"
import type {
	ExclusionRule,
	ExclusionRuleDraft,
	ExclusionRuleDryRunResult
} from "@/types/incidentManagement/exclusion-rules"
import { HttpClient } from "../../http-client"

export interface ExclusionRulesQuery {
	pagination: {
		skip?: number
		limit?: number
	}
	filters: {
		enabledOnly?: boolean
		/** Only rules created in-context from this alert. */
		sourceAlertId?: number
	}
}

export interface ExclusionRulePayload {
	name: string
	description: string
	channel: string
	title: string
	field_matches: { [key: string]: string }
	enabled: boolean
	customer_code?: string
	/** Provenance, create only: the backend ignores it on update. */
	source_alert_id?: number
}

/** The rule as the analyst is typing it — only the criteria the matcher evaluates. */
export type ExclusionRuleDryRunPayload = Partial<
	Pick<ExclusionRulePayload, "channel" | "title" | "field_matches" | "customer_code">
>

export default {
	getExclusionRulesList(args: Partial<ExclusionRulesQuery>, signal?: AbortSignal) {
		const params: {
			skip: number
			limit: number
			enabled_only?: boolean
			source_alert_id?: number
		} = {
			skip: args.pagination?.skip || 0,
			limit: args.pagination?.limit || 25
		}

		if (args.filters?.enabledOnly !== undefined) {
			params.enabled_only = args.filters.enabledOnly
		}
		if (args.filters?.sourceAlertId !== undefined) {
			params.source_alert_id = args.filters.sourceAlertId
		}

		return HttpClient.get<
			FlaskBaseResponse & {
				exclusions: ExclusionRule[]
				pagination: {
					total: number
					skip: number
					limit: number
				}
			}
		>(`/incidents/alerts/create/velo-sigma/exclusion`, { params, signal })
	},
	getExclusionRule(exclusionId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { exclusion_response: ExclusionRule }>(
			`/incidents/alerts/create/velo-sigma/exclusion/${exclusionId}`,
			{ signal }
		)
	},
	createExclusionRule(payload: ExclusionRulePayload) {
		return HttpClient.post<FlaskBaseResponse & { exclusion_response: ExclusionRule }>(
			`/incidents/alerts/create/velo-sigma/exclusion`,
			payload
		)
	},
	updateExclusionRule(exclusionId: number, payload: ExclusionRulePayload) {
		return HttpClient.patch<FlaskBaseResponse & { exclusion_response: ExclusionRule }>(
			`/incidents/alerts/create/velo-sigma/exclusion/${exclusionId}`,
			payload
		)
	},
	toggleExclusionRuleStatus(exclusionId: number) {
		return HttpClient.post<FlaskBaseResponse & { exclusion_response: ExclusionRule }>(
			`/incidents/alerts/velo-sigma/exclusion/${exclusionId}/toggle`
		)
	},
	/** Pre-fill a rule from a Velociraptor Sigma alert. 404 when the alert carries no Sigma payload. */
	getExclusionRuleDraft(alertId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { draft: ExclusionRuleDraft }>(
			`/incidents/alerts/alert/${alertId}/velo-sigma/exclusion-draft`,
			{ signal }
		)
	},
	/** Run the ingest-time matcher against the stored alert. Saves nothing. */
	dryRunExclusionRule(alertId: number, payload: ExclusionRuleDryRunPayload, signal?: AbortSignal) {
		return HttpClient.post<FlaskBaseResponse & ExclusionRuleDryRunResult>(
			`/incidents/alerts/alert/${alertId}/velo-sigma/exclusion-dry-run`,
			payload,
			{ signal }
		)
	},
	deleteExclusionRules(exclusionId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/alerts/create/velo-sigma/exclusion/${exclusionId}`)
	}
}
