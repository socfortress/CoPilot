import type { FlaskBaseResponse } from "@/types/flask.d"
import type { Organization } from "@/types/shuffle.d"
import { HttpClient } from "../httpClient"

export interface ShuffleConnectorCredentials {
	base_url: string
	api_key: string
}

export default {
	getOrganizations() {
		return HttpClient.get<FlaskBaseResponse & { data: Organization[]; total_count: number }>(
			`/shuffle/organizations/organizations?connector_name=Shuffle`
		)
	},
	getOrganization(organizationId: string) {
		return HttpClient.get<FlaskBaseResponse & { data: Organization }>(
			`/shuffle/organizations/organizations/${organizationId}?connector_name=Shuffle`
		)
	},
	// Returns the deployment-wide Shuffle connector base URL + API key for
	// the React MCP embeds. Backed by the connectors table.
	getConnectorCredentials() {
		return HttpClient.get<FlaskBaseResponse & ShuffleConnectorCredentials>(`/shuffle/integrations/credentials`)
	}
}
