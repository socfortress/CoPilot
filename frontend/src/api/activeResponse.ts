import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { ActiveResponseDetails, SupportedActiveResponse } from "@/types/activeResponse"

export interface InvokeRequest {
	activeResponseName: string
	action: "block" | "unblock"
	ip: string
	agentId?: string
}

export default {
	getSupported() {
		return HttpClient.get<FlaskBaseResponse & { supported_active_responses: SupportedActiveResponse[] }>(
			`/active_response/supported`
		)
	},
	getDetails(activeResponseName: string) {
		return HttpClient.get<FlaskBaseResponse & { active_response: ActiveResponseDetails }>(
			`/active_response/describe/${activeResponseName}`
		)
	},
	invoke(params: InvokeRequest) {
		const payload = {
			endpoint: "active-response",
			arguments: [],
			command: params.activeResponseName,
			custom: true,
			alert: {
				action: params.action,
				ip: params.ip
			},
			params: {
				wait_for_complete: true,
				agents_list: [params.agentId || "*"]
			}
		}
		return HttpClient.post<FlaskBaseResponse>(`/active_response/invoke`, payload)
	}
}
