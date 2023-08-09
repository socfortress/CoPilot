import { FlaskBaseResponse } from "@/types/flask"
import { Connector } from "@/types/connectors"
import { HttpClient } from "./httpClient"

export default {
    getAll() {
        return HttpClient.get<FlaskBaseResponse & { connectors: Connector[] }>("/connectors")
    },
    configure(connectorId, payload) {
        return HttpClient.post<FlaskBaseResponse & { connectors: Connector[] }>(`/connectors/${connectorId}`, payload)
    },
    update(connectorId, payload) {
        return HttpClient.put<FlaskBaseResponse & { connectors: Connector[] }>(`/connectors/${connectorId}`, payload)
    }
}
