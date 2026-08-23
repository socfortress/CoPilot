import type {
	CustomerPortalAiReportSettings,
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

export interface CustomerPortalAiReportSettingsPayload {
	enabled: boolean
}

type BrandingResponse = FlaskBaseResponse & {
	override: CustomerPortalBrandingOverride | null
	effective: CustomerPortalEffectiveBranding | null
}

type AiReportSettingsResponse = FlaskBaseResponse & {
	settings: CustomerPortalAiReportSettings
}

export default {
	getSettings(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { settings: CustomerPortalSettings }>(`/customer_portal/settings`, {
			signal
		})
	},
	setSettings(payload: CustomerPortalSettingsPayload) {
		return HttpClient.post<FlaskBaseResponse & { settings: CustomerPortalSettings }>(
			`/customer_portal/settings`,
			payload
		)
	},
	getBrandingOverrides(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { overrides: CustomerPortalBrandingListItem[] }>(
			`/customer_portal/branding`,
			{ signal }
		)
	},
	getCustomerBranding(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<BrandingResponse>(`/customer_portal/branding/${customerCode}`, { signal })
	},
	setCustomerBranding(customerCode: string, payload: CustomerPortalBrandingPayload) {
		return HttpClient.put<BrandingResponse>(`/customer_portal/branding/${customerCode}`, payload)
	},
	deleteCustomerBranding(customerCode: string) {
		return HttpClient.delete<BrandingResponse>(`/customer_portal/branding/${customerCode}`)
	},
	getCustomerAiReportSettings(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<AiReportSettingsResponse>(`/customer_portal/ai_reports/settings/${customerCode}`, {
			signal
		})
	},
	/** Admin-only: flips both portal AI surfaces for this customer at once. */
	setCustomerAiReportSettings(customerCode: string, payload: CustomerPortalAiReportSettingsPayload) {
		return HttpClient.put<AiReportSettingsResponse>(`/customer_portal/ai_reports/settings/${customerCode}`, payload)
	}
}
