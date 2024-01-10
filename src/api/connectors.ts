import { type FlaskBaseResponse } from "@/types/flask.d"
import type { Connector, ConnectorRequestPayload } from "@/types/connectors.d"
import { HttpClient } from "./httpClient"

export default {
	getAll() {
		return HttpClient.get<FlaskBaseResponse & { connectors: Connector[] }>("/connectors")
	},
	configure(connectorId: string | number, payload: ConnectorRequestPayload) {
		return HttpClient.post<FlaskBaseResponse & { connectors: Connector[] }>(`/connectors/${connectorId}`, payload)
	},
	update(connectorId: string | number, payload: ConnectorRequestPayload) {
		return HttpClient.put<FlaskBaseResponse & { connectors: Connector[] }>(`/connectors/${connectorId}`, payload)
	},
	verify(connectorId: string | number) {
		return HttpClient.post<FlaskBaseResponse & { connectionSuccessful: boolean }>(
			`/connectors/verify/${connectorId}`
		)
	},
	upload(connectorId: string | number, formData: FormData) {
		return HttpClient.post<FlaskBaseResponse & { connectors: Connector[] }>(
			`/connectors/upload/${connectorId}`,
			formData
		)
	}
}
