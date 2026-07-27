import type {
	CustomerPortalBrandingListItem,
	CustomerPortalBrandingOverride,
	CustomerPortalEffectiveBranding,
	CustomerPortalSettings
} from "@/types/customer-portal"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

export interface CustomerPortalSettingsPayload {
	title: string | null
	logo_base64: string | null
	logo_mime_type: string | null
	brand_color: string | null
}

/** Per-customer override payload. Null fields inherit the corresponding global setting. */
export interface CustomerPortalBrandingPayload extends CustomerPortalSettingsPayload {
	enabled: boolean
}

type BrandingResponse = FlaskBaseResponse & {
	override: CustomerPortalBrandingOverride | null
	effective: CustomerPortalEffectiveBranding | null
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
	},
	getBrandingOverrides() {
		return HttpClient.get<FlaskBaseResponse & { overrides: CustomerPortalBrandingListItem[] }>(
			`/customer_portal/branding`
		)
	},
	getCustomerBranding(customerCode: string) {
		return HttpClient.get<BrandingResponse>(`/customer_portal/branding/${customerCode}`)
	},
	setCustomerBranding(customerCode: string, payload: CustomerPortalBrandingPayload) {
		return HttpClient.put<BrandingResponse>(`/customer_portal/branding/${customerCode}`, payload)
	},
	deleteCustomerBranding(customerCode: string) {
		return HttpClient.delete<BrandingResponse>(`/customer_portal/branding/${customerCode}`)
	}
}
