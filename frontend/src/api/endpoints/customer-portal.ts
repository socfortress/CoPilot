import type {
	CustomerPortalAiReportSettings,
	CustomerPortalBrandingListItem,
	CustomerPortalBrandingOverride,
	CustomerPortalEffectiveBranding,
	CustomerPortalSettings,
	CustomerPortalSlaSettings
} from "@/types/customer-portal"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

export interface CustomerPortalSettingsPayload {
	title: string | null
	logo_base64: string | null
	logo_mime_type: string | null
	brand_color: string | null
}

/** Partial update of the global settings: only the fields present change; `reset` restores defaults. */
export interface CustomerPortalSettingsPatch {
	title?: string
	logo_base64?: string
	logo_mime_type?: string
	brand_color?: string
	reset?: ("title" | "logo" | "brand_color")[]
}

/** Per-customer override payload. Null fields inherit the corresponding global setting. */
export interface CustomerPortalBrandingPayload extends CustomerPortalSettingsPayload {
	enabled: boolean
}

export interface CustomerPortalAiReportSettingsPayload {
	enabled: boolean
	/** Left out: unchanged. */
	allow_customer_requests?: boolean
	/** Left out: unchanged; null: unlimited. */
	daily_request_limit?: number | null
}

type BrandingResponse = FlaskBaseResponse & {
	override: CustomerPortalBrandingOverride | null
	effective: CustomerPortalEffectiveBranding | null
}

type AiReportSettingsResponse = FlaskBaseResponse & {
	settings: CustomerPortalAiReportSettings
}

export interface CustomerPortalSlaSettingsPayload {
	enabled: boolean
}

type SlaSettingsResponse = FlaskBaseResponse & {
	settings: CustomerPortalSlaSettings
}

export default {
	/** Global settings with the inline logo, for the editor. The public `/settings` omits the logo bytes. */
	getSettings(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { settings: CustomerPortalSettings }>(
			`/customer_portal/settings/global`,
			{ signal }
		)
	},
	/** Change only the global settings sent (see `buildSettingsPatch`). */
	patchSettings(patch: CustomerPortalSettingsPatch) {
		return HttpClient.patch<FlaskBaseResponse>(`/customer_portal/settings`, patch)
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
	/** Admin-only: flips both portal AI surfaces for this customer at once, and whether its users may request analyses. */
	setCustomerAiReportSettings(customerCode: string, payload: CustomerPortalAiReportSettingsPayload) {
		return HttpClient.put<AiReportSettingsResponse>(`/customer_portal/ai_reports/settings/${customerCode}`, payload)
	},
	getCustomerSlaSettings(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<SlaSettingsResponse>(`/customer_portal/sla/settings/${customerCode}`, { signal })
	},
	/** Admin-only: shows or hides the portal's SLA page for this customer (#1187). */
	setCustomerSlaSettings(customerCode: string, payload: CustomerPortalSlaSettingsPayload) {
		return HttpClient.put<SlaSettingsResponse>(`/customer_portal/sla/settings/${customerCode}`, payload)
	}
}
