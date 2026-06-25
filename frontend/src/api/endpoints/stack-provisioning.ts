import type { FlaskBaseResponse } from "@/types/flask"
import type { AvailableContentPack } from "@/types/stack-provisioning"
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
	}
}
