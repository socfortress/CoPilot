import type { FlaskBaseResponse } from "@/types/flask"
import type { AvailableContentPack, AvailableInfluxDbCheck, ProvisionedInfluxDbCheck } from "@/types/stack-provisioning"
import { HttpClient } from "../http-client"

export default {
	getAvailableContentPacks() {
		return HttpClient.get<FlaskBaseResponse & { available_content_packs: AvailableContentPack[] }>(
			`/stack_provisioning/graylog/available/content_packs`
		)
	},
	provisionContentPack(contentPackName: string) {
		return HttpClient.post<FlaskBaseResponse>(`/stack_provisioning/graylog/provision/content_pack`, {
			content_pack_name: contentPackName
		})
	},
	getAvailableInfluxDbChecks() {
		return HttpClient.get<FlaskBaseResponse & { available_checks: AvailableInfluxDbCheck[] }>(
			`/stack_provisioning/influxdb/available/checks`
		)
	},
	provisionInfluxDbCheck(checkName: string, overwrite: boolean = false) {
		return HttpClient.post<FlaskBaseResponse & { results: ProvisionedInfluxDbCheck[] }>(
			`/stack_provisioning/influxdb/provision/check`,
			{
				check_name: checkName,
				overwrite
			}
		)
	},
	provisionInfluxDbChecks(overwrite: boolean = false) {
		return HttpClient.post<FlaskBaseResponse & { results: ProvisionedInfluxDbCheck[] }>(
			`/stack_provisioning/influxdb/provision/checks`,
			{ overwrite }
		)
	},
	decommissionInfluxDbCheck(checkName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/stack_decommissioning/influxdb/check/${checkName}`)
	}
}
