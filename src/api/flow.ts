import { HttpClient } from "./httpClient"
import type { FlaskBaseResponse } from "@/types/flask.d"
import type { CollectResult, FlowResult } from "@/types/flow.d"

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
