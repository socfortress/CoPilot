import { HttpClient } from "./httpClient"
import type { FlaskBaseResponse } from "@/types/flask.d"
import type { EvaluationData, ThreatIntelResponse } from "@/types/threatIntel.d"

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
	}
}
