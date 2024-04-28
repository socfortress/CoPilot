import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { NetworkConnector } from "@/types/networkConnectors"

export default {
	getAvailableNetworkConnectors() {
		return HttpClient.get<FlaskBaseResponse & { network_connector_keys: NetworkConnector[] }>(
			`/network_connectors/available_network_connectors`
		)
	}
}
