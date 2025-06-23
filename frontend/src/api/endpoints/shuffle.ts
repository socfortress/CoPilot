import type { FlaskBaseResponse } from "@/types/flask.d"
import type { Organization } from "@/types/shuffle.d"
import { HttpClient } from "../httpClient"

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
	}
}
