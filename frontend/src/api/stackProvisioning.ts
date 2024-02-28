import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { AvailableContentPack } from "@/types/stackProvisioning"

export default {
	getAvailableContentPacks() {
		return HttpClient.get<FlaskBaseResponse & { available_content_packs: AvailableContentPack[] }>(
			`/stack_provisioning/graylog/available/content_packs`
		)
	},
	deploy(contentPackName: string) {
		return HttpClient.post<FlaskBaseResponse>(`/stack_provisioning/graylog/available/content_packs`, {
			content_pack_name: contentPackName
		})
	}
}
