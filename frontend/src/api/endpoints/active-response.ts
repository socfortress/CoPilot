import type { ActiveResponseDetails, SupportedActiveResponse } from "@/types/active-response"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

export type InvokeRequestAction = "block" | "unblock"

export interface InvokeRequest {
	activeResponseName: string
	action: InvokeRequestAction
	ip: string
	agentId?: string
}

export default {
	getSupported(query: { agentId?: string }, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { supported_active_responses: SupportedActiveResponse[] }>(
			`/active_response/supported${query.agentId ? `/${query.agentId}` : ""}`,
			{ signal }
		)
	},
	getDetails(activeResponseName: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { active_response: ActiveResponseDetails }>(
			`/active_response/describe/${activeResponseName.toLowerCase()}`,
			{ signal }
		)
	},
	invoke(params: InvokeRequest) {
		const payload = {
			endpoint: "/active-response",
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
