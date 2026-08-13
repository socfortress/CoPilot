import type { FlaskBaseResponse } from "@/types/flask"
import type { SourceConfiguration, SourceName } from "@/types/incidentManagement/sources"
import { HttpClient } from "../../http-client"

export default {
	getConfiguredSources(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { sources: SourceName[] }>(
			`/incidents/db_operations/configured/sources`,
			{ signal }
		)
	},
	getAvailableMappings(indexName: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { available_mappings: string[] }>(
			`/incidents/db_operations/mappings/fields-assets-title-and-timefield`,
			{ params: { index_name: indexName }, signal }
		)
	},
	getSourceByIndex(indexName: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { source: SourceName }>(
			`/incidents/db_operations/available-source/${indexName}`,
			{ signal }
		)
	},
	getAvailableIndices(source: SourceName, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { indices: string[] }>(
			`/incidents/db_operations/available-indices/${source}`,
			{ signal }
		)
	},
	createSourceConfiguration(payload: SourceConfiguration) {
		return HttpClient.post<FlaskBaseResponse>(`/incidents/db_operations/fields-assets-title-and-timefield`, payload)
	},
	updateSourceConfiguration(payload: SourceConfiguration) {
		return HttpClient.put<FlaskBaseResponse>(`/incidents/db_operations/fields-assets-title-and-timefield`, payload)
	},
	getSourceConfiguration(source: SourceName, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & SourceConfiguration>(
			`/incidents/db_operations/fields-assets-title-and-timefield`,
			{ params: { source }, signal }
		)
	},
	getSocfortressRecommendsWazuh(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & SourceConfiguration>(
			`/incidents/db_operations/socfortress/recommends/wazuh`,
			{ signal }
		)
	},
	deleteSourceConfiguration(source: SourceName) {
		return HttpClient.delete<FlaskBaseResponse>(`/incidents/db_operations/configured/sources/${source}`)
	}
}
