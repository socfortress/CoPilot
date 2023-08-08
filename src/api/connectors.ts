import { FlaskBaseResponse } from "@/types/flask"
import { Connector } from "@/types/connectors"
import { HttpClient } from "./httpClient"

export default {
    getAll() {
        return HttpClient.get<FlaskBaseResponse & { connectors: Connector[] }>("/connectors")
    }
}
