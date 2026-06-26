import type { FlaskBaseResponse } from "@/types/flask"
import type { CollectResult, FlowResult } from "@/types/flow"
import { HttpClient } from "../http-client"

export default {
	getAllByAgent(hostname: string) {
		return HttpClient.get<FlaskBaseResponse & { results: FlowResult[] }>(`/flows/${hostname}`)
	},
	retrieve(clientId: string, sessionId: string) {
		return HttpClient.post<FlaskBaseResponse & { results: CollectResult[] }>(`/flows/retrieve`, {
			client_id: clientId,
			session_id: sessionId
		})
	}
}
