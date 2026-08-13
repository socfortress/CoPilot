import type { FlaskBaseResponse } from "@/types/flask"
import type { Organization } from "@/types/shuffle"
import { HttpClient } from "../http-client"

export interface ShuffleConnectorCredentials {
	base_url: string
	api_key: string
}

export default {
	getOrganizations(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { data: Organization[]; total_count: number }>(
			`/shuffle/organizations/organizations?connector_name=Shuffle`,
			{ signal }
		)
	},
	getOrganization(organizationId: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { data: Organization }>(
			`/shuffle/organizations/organizations/${organizationId}?connector_name=Shuffle`,
			{ signal }
		)
	},
	// Returns the deployment-wide Shuffle connector base URL + API key for
	// the React MCP embeds. Backed by the connectors table.
	getConnectorCredentials(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & ShuffleConnectorCredentials>(`/shuffle/integrations/credentials`, {
			signal
		})
	}
}
