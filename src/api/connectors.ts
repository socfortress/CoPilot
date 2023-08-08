import { HttpClient } from "./httpClient"

export default {
    getAll() {
        // TODO: implement res type
        return HttpClient.get("/connectors")
    }
}
