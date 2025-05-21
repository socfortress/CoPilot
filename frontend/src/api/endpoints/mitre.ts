/* eslint-disable jsdoc/no-multi-asterisks */
import type { FlaskBaseResponse } from "@/types/flask.d"
import type {
	MitreAtomicTest,
	MitreEventDetails,
	MitreGroupDetails,
	MitreMitigationDetails,
	MitreSoftwareDetails,
	MitreTacticDetails,
	MitreTechnique,
	MitreTechniqueDetails
} from "@/types/mitre.d"
import { HttpClient } from "../httpClient"

export type MitreTechniquesAlertsQueryTimeRange = `${number}${"h" | "d" | "w"}`

export interface MitreTechniquesAlertsQuery {
	/** Time range for the search (e.g., now-24h, now-7d) */
	time_range?: MitreTechniquesAlertsQueryTimeRange
	/** Maximum number of techniques to return per page */
	size?: number
	/** Page number for pagination */
	page?: number
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

export interface MitreMitigationsQuery {
	id: string
}

export interface MitreSoftwareQuery {
	id: string
}

export interface MitreTacticsQuery {
	id: string
}

export interface MitreEventsQuery {
	/** MITRE ATT&CK technique ID (e.g., T1047, 1047) */
	technique_id: string
	/** Time range for the search (e.g., now-24h, now-7d) */
	time_range?: string
	/** Maximum number of techniques to return per page */
	size?: number
	/** Page number for pagination */
	page?: number
	/** Filter by rule level */
	rule_level?: string
	/** Filter by rule group */
	rule_group?: string
	/** Override the field containing MITRE IDs */
	mitre_field?: string
	/** Index pattern to search; Default value : wazuh-* */
	index_pattern?: string
}

export interface MitreAtomicTestsQuery {
	/** Maximum number of techniques to return per page */
	size?: number
	/** Page number for pagination */
	page?: number
}

export default {
	getMitreTechniquesAlerts(query: MitreTechniquesAlertsQuery, signal?: AbortSignal) {
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
			},
			signal
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

		return HttpClient.get<FlaskBaseResponse & { results: MitreGroupDetails[]; total: number }>(
			`/wazuh_manager/mitre/groups`,
			{
				params: {
					q
				}
			}
		)
	},
	getMitreMitigations(query?: MitreMitigationsQuery) {
		let q: string | undefined

		if (query?.id) {
			q = `id=${query?.id}`
		}

		return HttpClient.get<FlaskBaseResponse & { results: MitreMitigationDetails[]; total: number }>(
			`/wazuh_manager/mitre/mitigations`,
			{
				params: {
					q
				}
			}
		)
	},
	getMitreSoftware(query?: MitreSoftwareQuery) {
		let q: string | undefined

		if (query?.id) {
			q = `id=${query?.id}`
		}

		return HttpClient.get<FlaskBaseResponse & { results: MitreSoftwareDetails[] }>(
			`/wazuh_manager/mitre/software`,
			{
				params: {
					q
				}
			}
		)
	},
	getMitreTactics(query?: MitreTacticsQuery) {
		let q: string | undefined

		if (query?.id) {
			q = `id=${query?.id}`
		}

		return HttpClient.get<FlaskBaseResponse & { results: MitreTacticDetails[] }>(`/wazuh_manager/mitre/tactics`, {
			params: {
				q
			}
		})
	},
	getMitreEvents(query: MitreEventsQuery, signal?: AbortSignal) {
		return HttpClient.get<
			FlaskBaseResponse & {
				technique_id: string
				technique_name: string
				total_alerts: number
				alerts: MitreEventDetails[]
				field_used: string
				time_range: string
			}
		>(`/wazuh_manager/mitre/techniques/${query.technique_id}/alerts`, {
			params: {
				time_range: query?.time_range || "now-24h",
				size: query?.size || 25,
				page: query?.page || 1,
				rule_level: query?.rule_level,
				rule_group: query?.rule_group,
				mitre_field: query?.mitre_field,
				index_pattern: query?.index_pattern || "wazuh-*"
			},
			signal
		})
	},
	getMitreAtomicTests(query?: MitreAtomicTestsQuery) {
		return HttpClient.get<
			FlaskBaseResponse & {
				total_techniques: number
				total_tests: number
				tests: MitreAtomicTest[]
				last_updated: Date
				page: number
				page_size: number
				total_pages: number
			}
		>(`/wazuh_manager/mitre/atomic-tests`, {
			params: {
				size: query?.size || 25,
				page: query?.page || 1
			}
		})
	},
	getMitreAtomicTestContent(technique_id: string) {
		return HttpClient.get<
			FlaskBaseResponse & {
				technique_id: string
				markdown_content: string
			}
		>(`/wazuh_manager/mitre/techniques/${technique_id}/alerts`)
	}
}
