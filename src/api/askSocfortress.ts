import { HttpClient } from "./httpClient"
import type { FlaskBaseResponse } from "@/types/flask.d"

export default {
	create(indexName: string, alertId: string) {
		const body = {
			index_name: indexName,
			alert_id: alertId
		}
		return HttpClient.post<FlaskBaseResponse>(`/ask_socfortress/sigma`, body)
	}
}
