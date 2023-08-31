import { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "./httpClient"
import { Agents } from "@/types/agents"

export default {
    getAgents() {
        return HttpClient.get<FlaskBaseResponse & { agents: Agents[] }>("/agents")
    }
}
