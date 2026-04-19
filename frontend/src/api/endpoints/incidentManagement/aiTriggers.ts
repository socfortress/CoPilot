import type { FlaskBaseResponse } from "@/types/flask.d"
import type { AITrigger } from "@/types/incidentManagement/aiTriggers.d"
import { HttpClient } from "../../httpClient"

export interface AITriggerPayload {
	customer_code: string
	enabled: boolean
}

export default {
	getAITriggers(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { ai_triggers: AITrigger[] }>(
			`/incidents/db_operations/ai_trigger/${customerCode}`
		)
	},
	setAITrigger(notification: AITriggerPayload) {
		return HttpClient.put<FlaskBaseResponse & { ai_triggers: AITrigger[] }>(
			`/incidents/db_operations/ai_trigger`,
			notification,
			{
				params: {
					customer_code: notification.customer_code
				}
			}
		)
	}
}
