import type { FlaskBaseResponse } from "@/types/flask.d"
import type { SourceConfiguration, SourceName } from "@/types/incidentManagement/sources.d"
import { HttpClient } from "../../httpClient"

export default {
	getConfiguredSources() {
		return HttpClient.get<FlaskBaseResponse & { sources: SourceName[] }>(
			`/incidents/db_operations/configured/sources`
		)
	},
	getAvailableMappings(indexName: string) {
		return HttpClient.get<FlaskBaseResponse & { available_mappings: string[] }>(
			`/incidents/db_operations/mappings/fields-assets-title-and-timefield`,
			{
				params: { index_name: indexName }
			}
		)
	},
	getSourceByIndex(indexName: string) {
		return HttpClient.get<FlaskBaseResponse & { source: SourceName }>(
			`/incidents/db_operations/available-source/${indexName}`
		)
	},
	getAvailableIndices(source: SourceName) {
		return HttpClient.get<FlaskBaseResponse & { indices: string[] }>(
			`/incidents/db_operations/available-indices/${source}`
		)
	},
	createSourceConfiguration(payload: SourceConfiguration) {
		return HttpClient.post<FlaskBaseResponse>(`/incidents/db_operations/fields-assets-title-and-timefield`, payload)
	},
	updateSourceConfiguration(payload: SourceConfiguration) {
		return HttpClient.put<FlaskBaseResponse>(`/incidents/db_operations/fields-assets-title-and-timefield`, payload)
	},
	getSourceConfiguration(source: SourceName) {
		return HttpClient.get<FlaskBaseResponse & SourceConfiguration>(
			`/incidents/db_operations/fields-assets-title-and-timefield`,
			{
				params: { source }
			}
		)
	},
	getSocfortressRecommendsWazuh() {
		return HttpClient.get<FlaskBaseResponse & SourceConfiguration>(
			`/incidents/db_operations/socfortress/recommends/wazuh`
		)
	},
	deleteSourceConfiguration(source: SourceName) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/configured/sources/${source}`)
	}
}
