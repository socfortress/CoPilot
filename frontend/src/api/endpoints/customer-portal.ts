import type { CustomerPortalSettings } from "@/types/customer-portal"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

export interface CustomerPortalSettingsPayload {
	title: string | null
	logo_base64: string | null
	logo_mime_type: string | null
	brand_color: string | null
}

export default {
	getSettings() {
		return HttpClient.get<FlaskBaseResponse & { settings: CustomerPortalSettings }>(`/customer_portal/settings`)
	},
	setSettings(payload: CustomerPortalSettingsPayload) {
		return HttpClient.post<FlaskBaseResponse & { settings: CustomerPortalSettings }>(
			`/customer_portal/settings`,
			payload
		)
	}
}
