import type {
	AuthenticationResponseJSON,
	PublicKeyCredentialCreationOptionsJSON,
	PublicKeyCredentialRequestOptionsJSON,
	RegistrationResponseJSON
} from "@simplewebauthn/browser"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export interface PasskeyStatusResponse {
	enabled: boolean
	count?: number
}

export interface PasskeyItem {
	id: number
	device_name: string
	created_at: string
	last_used_at: string | null
	transports: string[]
}

export interface PasskeyListResponse {
	passkeys: PasskeyItem[]
}

export interface PasskeyLoginResponse {
	access_token: string
	token_type: string
	requires_2fa?: boolean
}

export type PasskeyRegisterOptions = PublicKeyCredentialCreationOptionsJSON & {
	challengeToken: string
	deviceName?: string
}

export type PasskeyLoginOptions = PublicKeyCredentialRequestOptionsJSON & {
	challengeToken: string
}

export interface PasskeyVerifyPayload {
	challenge_token: string
	credential: RegistrationResponseJSON | AuthenticationResponseJSON
	device_name?: string
}

export interface PasskeyRegisterOptionsQuery {
	device_name?: string
}

export interface PasskeyLoginOptionsQuery {
	username?: string
}

export default {
	getPublicStatus() {
		return HttpClient.get<FlaskBaseResponse & PasskeyStatusResponse>("/auth/passkey/status")
	},

	getMyStatus() {
		return HttpClient.get<FlaskBaseResponse & PasskeyStatusResponse>("/auth/passkey/me/status")
	},

	listMine() {
		return HttpClient.get<FlaskBaseResponse & PasskeyListResponse>("/auth/passkey/me")
	},

	registerOptions(query: PasskeyRegisterOptionsQuery = {}) {
		return HttpClient.post<PasskeyRegisterOptions>("/auth/passkey/register/options", query)
	},

	registerVerify(payload: PasskeyVerifyPayload) {
		return HttpClient.post<FlaskBaseResponse>("/auth/passkey/register/verify", payload)
	},

	loginOptions(query: PasskeyLoginOptionsQuery = {}) {
		return HttpClient.post<PasskeyLoginOptions>("/auth/passkey/login/options", query)
	},

	loginVerify(payload: PasskeyVerifyPayload) {
		return HttpClient.post<FlaskBaseResponse & PasskeyLoginResponse>("/auth/passkey/login/verify", payload)
	},

	remove(passkeyId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/auth/passkey/${passkeyId}`)
	}
}
