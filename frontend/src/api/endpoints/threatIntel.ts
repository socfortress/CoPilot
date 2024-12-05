import type { FlaskBaseResponse } from "@/types/flask.d"
import type {
	AiAnalysisResponse,
	AiVelociraptorArtifactRecommendationResponse,
	AiWazuhExclusionRuleResponse,
	EpssScore,
	EvaluationData,
	ThreatIntelResponse,
	VirusTotalResponse
} from "@/types/threatIntel.d"
import { HttpClient } from "../httpClient"

export default {
	create(iocValue: string) {
		const body = {
			ioc_value: iocValue
		}
		return HttpClient.post<FlaskBaseResponse & { data: ThreatIntelResponse }>(`/threat_intel/socfortress`, body)
	},
	processNameEvaluation(processName: string) {
		const body = {
			process_name: processName
		}
		return HttpClient.post<FlaskBaseResponse & { data: EvaluationData }>(`/threat_intel/process_name`, body)
	},
	epssScore(cve: string) {
		const body = {
			cve
		}
		return HttpClient.post<FlaskBaseResponse & { data: EpssScore[]; the_epss_model: string }>(
			`/threat_intel/epss`,
			body
		)
	},
	aiAlertAnalysis({ indexId, indexName, alertId }: { indexId: string; indexName: string; alertId: number }) {
		return HttpClient.post<FlaskBaseResponse & AiAnalysisResponse>(`/threat_intel/ai/analyze-alert`, {
			index_name: indexName,
			index_id: indexId,
			alert_id: alertId
		})
	},
	aiWazuhExclusionRule({ indexId, indexName, alertId }: { indexId: string; indexName: string; alertId: number }) {
		return HttpClient.post<FlaskBaseResponse & AiWazuhExclusionRuleResponse>(
			`/threat_intel/ai/wazuh-exclusion-rule`,
			{
				index_name: indexName,
				index_id: indexId,
				alert_id: alertId
			}
		)
	},
	aiVelociraptorArtifactRecommendation({
		indexId,
		indexName,
		agentId,
		alertId
	}: {
		indexId: string
		indexName: string
		agentId: string
		alertId: number
	}) {
		return HttpClient.post<FlaskBaseResponse & AiVelociraptorArtifactRecommendationResponse>(
			`/threat_intel/ai/velociraptor-artifact-recommendation`,
			{
				index_name: indexName,
				index_id: indexId,
				agent_id: agentId,
				alert_id: alertId
			}
		)
	},
	virusTotalEnrichment(iocValue: string) {
		return HttpClient.post<FlaskBaseResponse & VirusTotalResponse>(`/threat_intel/virustotal`, {
			ioc_value: iocValue
		})
	}
}
