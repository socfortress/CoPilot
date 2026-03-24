import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export interface SSOConfigResponse {
	sso_enabled: boolean
	azure_enabled: boolean
	azure_tenant_id: string | null
	azure_client_id: string | null
	azure_client_secret_set: boolean
	azure_redirect_uri: string | null
	google_enabled: boolean
	google_client_id: string | null
	google_client_secret_set: boolean
	google_redirect_uri: string | null
	cf_enabled: boolean
	cf_team_domain: string | null
	cf_audience: string | null
	message: string
	success: boolean
}

export interface SSOConfigUpdate {
	sso_enabled: boolean
	azure_enabled: boolean
	azure_tenant_id?: string | null
	azure_client_id?: string | null
	azure_client_secret?: string | null
	azure_redirect_uri?: string | null
	google_enabled: boolean
	google_client_id?: string | null
	google_client_secret?: string | null
	google_redirect_uri?: string | null
	cf_enabled: boolean
	cf_team_domain?: string | null
	cf_audience?: string | null
}

export interface SSOAllowedEmail {
	id: number
	email: string
	role_id: number
	created_at: string
}

export interface SSOAllowedEmailInput {
	email: string
	role_id: number
}

export interface SSOPublicStatus {
	sso_enabled: boolean
	azure_enabled: boolean
	google_enabled: boolean
	cf_enabled: boolean
	azure_authorization_url: string | null
	google_authorization_url: string | null
}

export default {
	/** Public — which SSO providers are active */
	getStatus() {
		return HttpClient.get<SSOPublicStatus>("/auth/sso/status")
	},

	/** Admin — get SSO settings */
	getSettings() {
		return HttpClient.get<SSOConfigResponse>("/auth/sso/settings")
	},

	/** Admin — update SSO settings */
	updateSettings(payload: SSOConfigUpdate) {
		return HttpClient.put<SSOConfigResponse>("/auth/sso/settings", payload)
	},

	/** Admin — list allowed emails */
	getAllowedEmails() {
		return HttpClient.get<FlaskBaseResponse & { emails: SSOAllowedEmail[] }>("/auth/sso/allowed-emails")
	},

	/** Admin — add allowed email */
	addAllowedEmail(payload: SSOAllowedEmailInput) {
		return HttpClient.post<FlaskBaseResponse & { id: number }>("/auth/sso/allowed-emails", payload)
	},

	/** Admin — remove allowed email */
	removeAllowedEmail(emailId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/auth/sso/allowed-emails/${emailId}`)
	},

	/** Cloudflare Access — verify JWT from header */
	cloudflareVerify() {
		return HttpClient.post<FlaskBaseResponse & { access_token: string; token_type: string; requires_2fa?: boolean }>(
			"/auth/sso/cloudflare/verify"
		)
	}
}
