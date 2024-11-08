import type { FlaskBaseResponse } from "@/types/flask.d"
import type { AiAnalysisResponse, EpssScore, EvaluationData, ThreatIntelResponse } from "@/types/threatIntel.d"
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
	aiAlertAnalysis({ indexId, indexName }: { indexId: string; indexName: string }) {
		return HttpClient.post<FlaskBaseResponse & AiAnalysisResponse>(`/threat_intel/ai/analyze-alert`, {
			index_name: indexName,
			index_id: indexId
		})
	}
}
