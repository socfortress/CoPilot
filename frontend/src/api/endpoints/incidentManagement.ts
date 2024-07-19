import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"
import type { SourceConfiguration } from "@/types/incidentManagement.d"

export type SourceConfigurationPayload = SourceConfiguration

export default {
	getConfiguredSources() {
		return HttpClient.get<FlaskBaseResponse & { sources: string[] }>(`/incidents/db_operations/configured/sources`)
	},
	getAvailableMappings(indexName: string) {
		return HttpClient.get<FlaskBaseResponse & { available_mappings: string[] }>(
			`/incidents/db_operations/mappings/fields-assets-title-and-timefield`,
			{
				params: { index_name: indexName }
			}
		)
	},
	setSourceConfiguration(payload: SourceConfigurationPayload) {
		return HttpClient.post<FlaskBaseResponse>(`/incidents/db_operations/fields-assets-title-and-timefield`, payload)
	},
	getSourceConfiguration(source: string) {
		return HttpClient.get<FlaskBaseResponse & SourceConfiguration>(
			`/incidents/db_operations/fields-assets-title-and-timefield`,
			{
				params: { source }
			}
		)
	},
	deleteSourceConfiguration(source: string) {
		return HttpClient.delete<FlaskBaseResponse & SourceConfiguration>(
			`/incidents/db_operations/configured/sources/${source}`
		)
	}
}
