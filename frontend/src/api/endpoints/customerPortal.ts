import type { CustomerPortalSettings } from "@/types/customerPortal.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export interface CustomerPortalSettingsPayload {
	title: string
	logo_base64: string
	logo_mime_type: string
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
