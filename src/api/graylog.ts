import { HttpClient } from "./httpClient"
import { FlaskBaseResponse } from "@/types/flask"
import { Message, ThroughputMetric, IndexData, Inputs } from "@/types/graylog" // Import Graylog interfaces

export default {
    getMessages() {
        return HttpClient.get<FlaskBaseResponse & { messages: Message[] }>(`/graylog/messages`)
    },
    getMetrics() {
        return HttpClient.get<FlaskBaseResponse & { metrics: ThroughputMetric[] }>(`/graylog/metrics`)
    },
    getIndices() {
        return HttpClient.get<FlaskBaseResponse & { indexData: IndexData }>(`/graylog/indices`)
    },
    deleteIndex(indexName: string) {
        return HttpClient.delete<FlaskBaseResponse>(`/graylog/indices/${indexName}/delete`)
    },
    getInputs() {
        return HttpClient.get<FlaskBaseResponse & { inputs: Inputs }>(`/graylog/inputs`)
    }
}
