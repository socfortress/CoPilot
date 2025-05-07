/* eslint-disable jsdoc/no-multi-asterisks */
import type { FlaskBaseResponse } from "@/types/flask.d"
import type { MitreTechnique, MitreTechniqueDetails } from "@/types/mitre.d"
import { HttpClient } from "../httpClient"

export interface MitreTechniquesAlertsQuery {
	/** Time range for the search (e.g., now-24h, now-7d) */
	time_range: string
	/** Maximum number of techniques to return per page */
	size: number
	/** Page number for pagination */
	page: number
	/** Filter by rule level */
	rule_level?: string
	/** Filter by rule group */
	rule_group?: string
	/** Override the field containing MITRE IDs */
	mitre_field?: string
	/** Index pattern to search; Default value : wazuh-* */
	index_pattern?: string
}

export interface MitreTechniqueDetailsQuery {
	external_id: string
}

export interface MitreGroupsQuery {
	id: string
}

export default {
	getMitreTechniquesAlerts(query?: MitreTechniquesAlertsQuery) {
		return HttpClient.get<
			FlaskBaseResponse & {
				total_alerts: number
				techniques_count: number
				techniques: MitreTechnique[]
				time_range: string
				field_used: string
				page: number
				page_size: number
				total_pages: number
			}
		>(`/wazuh_manager/mitre/techniques/alerts`, {
			params: {
				time_range: query?.time_range || "now-24h",
				size: query?.size || 25,
				page: query?.page || 1,
				rule_level: query?.rule_level,
				rule_group: query?.rule_group,
				mitre_field: query?.mitre_field,
				index_pattern: query?.index_pattern || "wazuh-*"
			}
		})
	},
	getMitreTechniqueDetails(query?: MitreTechniqueDetailsQuery) {
		let q: string | undefined

		if (query?.external_id) {
			q = `external_id=${query?.external_id}`
		}

		return HttpClient.get<FlaskBaseResponse & { results: MitreTechniqueDetails[] }>(
			`/wazuh_manager/mitre/techniques`,
			{
				params: {
					q
				}
			}
		)
	},
	getMitreGroups(query?: MitreGroupsQuery) {
		let q: string | undefined

		if (query?.id) {
			q = `id=${query?.id}`
		}

		return HttpClient.get<FlaskBaseResponse & { results: MitreTechniqueDetails[] }>(`/wazuh_manager/mitre/groups`, {
			params: {
				q
			}
		})
	}
}
