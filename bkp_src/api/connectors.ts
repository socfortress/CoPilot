import { FlaskBaseResponse } from "@/types/flask"
import { Connector, ConnectorRequestPayload } from "@/types/connectors"
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
    upload(connectorId: string | number, formData: FormData) {
        return HttpClient.post<FlaskBaseResponse & { connectors: Connector[] }>(`/connectors/upload`, formData)
    }
}
