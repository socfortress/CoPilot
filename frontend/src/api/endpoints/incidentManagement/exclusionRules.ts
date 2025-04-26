import type { FlaskBaseResponse } from "@/types/flask.d"
import type { ExclusionRule } from "@/types/incidentManagement/exclusionRules.d"
import { HttpClient } from "../../httpClient"

export interface ExclusionRulesQuery {
	pagination: {
		skip?: number
		limit?: number
	}
	filters: {
		enabledOnly?: boolean
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
}

export default {
	getExclusionRulesList(args: Partial<ExclusionRulesQuery>, signal?: AbortSignal) {
		const params: any = {
			skip: args.pagination?.skip || 0,
			limit: args.pagination?.limit || 25
		}

		if (args.filters?.enabledOnly !== undefined) {
			params.enabled_only = args.filters.enabledOnly
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
	deleteExclusionRules(exclusionId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/alerts/create/velo-sigma/exclusion/${exclusionId}`)
	}
}
