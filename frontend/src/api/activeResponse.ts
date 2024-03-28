import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { ActiveResponseDetails, SupportedActiveResponse } from "@/types/activeResponse.d"

export type InvokeRequestAction = "block" | "unblock"

export interface InvokeRequest {
	activeResponseName: string
	action: InvokeRequestAction
	ip: string
	agentId?: string
}

export default {
	getSupported(agentId?: string) {
		return HttpClient.get<FlaskBaseResponse & { supported_active_responses: SupportedActiveResponse[] }>(
			`/active_response/supported${agentId ? "/" + agentId : ""}`
		)
	},
	getDetails(activeResponseName: string) {
		return HttpClient.get<FlaskBaseResponse & { active_response: ActiveResponseDetails }>(
			`/active_response/describe/${activeResponseName.toLowerCase()}`
		)
	},
	invoke(params: InvokeRequest) {
		const payload = {
			endpoint: "active-response",
			arguments: [],
			command: params.activeResponseName.toLowerCase(),
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
