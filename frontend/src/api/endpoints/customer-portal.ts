import type {
	CustomerPortalActivitySettings,
	CustomerPortalAiReportSettings,
	CustomerPortalBrandingListItem,
	CustomerPortalBrandingOverride,
	CustomerPortalEffectiveBranding,
	CustomerPortalExposureSettings,
	CustomerPortalNotificationSettings,
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
	theme_from_brand_color?: boolean
	reset?: ("title" | "logo" | "brand_color" | "theme_from_brand_color")[]
}

/** Per-customer override payload. Null fields inherit the corresponding global setting. */
export interface CustomerPortalBrandingPayload extends CustomerPortalSettingsPayload {
	enabled: boolean
	/** Theme the portal with the brand color; null inherits the global choice. */
	theme_from_brand_color: boolean | null
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

export interface CustomerPortalActivitySettingsPayload {
	enabled: boolean
}

type ActivitySettingsResponse = FlaskBaseResponse & {
	settings: CustomerPortalActivitySettings
}

export interface CustomerPortalExposureSettingsPayload {
	enabled: boolean
}

type ExposureSettingsResponse = FlaskBaseResponse & {
	settings: CustomerPortalExposureSettings
}

export interface CustomerPortalNotificationSettingsPayload {
	enabled: boolean
}

type NotificationSettingsResponse = FlaskBaseResponse & {
	settings: CustomerPortalNotificationSettings
	/** Whether SMTP is configured: without it, portal users get the bell only. */
	email_configured: boolean
	/** The UTC hour of the daily summary. */
	digest_hour_utc: number
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
	},
	getCustomerActivitySettings(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<ActivitySettingsResponse>(`/customer_portal/activity/settings/${customerCode}`, {
			signal
		})
	},
	/** Admin-only: shows or hides the portal's Activity page for this customer (#1284). */
	setCustomerActivitySettings(customerCode: string, payload: CustomerPortalActivitySettingsPayload) {
		return HttpClient.put<ActivitySettingsResponse>(`/customer_portal/activity/settings/${customerCode}`, payload)
	},
	getCustomerNotificationSettings(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<NotificationSettingsResponse>(`/customer_portal/notifications/settings/${customerCode}`, {
			signal
		})
	},
	/** Admin-only: turns portal users' notifications on or off for this customer (#1282). */
	setCustomerNotificationSettings(customerCode: string, payload: CustomerPortalNotificationSettingsPayload) {
		return HttpClient.put<NotificationSettingsResponse>(
			`/customer_portal/notifications/settings/${customerCode}`,
			payload
		)
	},
	getCustomerExposureSettings(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<ExposureSettingsResponse>(`/customer_portal/exposure/settings/${customerCode}`, {
			signal
		})
	},
	/** Admin-only: shows or hides the portal's Exposure page for this customer (#1289). */
	setCustomerExposureSettings(customerCode: string, payload: CustomerPortalExposureSettingsPayload) {
		return HttpClient.put<ExposureSettingsResponse>(`/customer_portal/exposure/settings/${customerCode}`, payload)
	}
}
