import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export interface TOTPSetupResponse {
	secret: string
	otpauth_url: string
	qr_data_uri: string
	backup_codes: string[]
}

export interface TOTPStatusResponse {
	enabled: boolean
}

export interface TOTPBackupCodesResponse {
	backup_codes: string[]
}

export interface TOTPValidateResponse {
	access_token: string
	token_type: string
}

export interface TOTPValidateRequest {
	temp_token: string
	code?: string
	backup_code?: string
}

export interface TOTPDeleteRequest {
	code?: string
	backup_code?: string
}

export default {
	/** Get 2FA status for current user */
	getStatus() {
		return HttpClient.get<FlaskBaseResponse & TOTPStatusResponse>("/auth/2fa/status")
	},

	/** Start 2FA setup — get QR code and backup codes */
	setup() {
		return HttpClient.post<FlaskBaseResponse & TOTPSetupResponse>("/auth/2fa/setup")
	},

	/** Verify setup with a TOTP code to activate 2FA */
	verifySetup(code: string) {
		return HttpClient.post<FlaskBaseResponse>("/auth/2fa/verify-setup", { code })
	},

	/** Disable 2FA (requires TOTP code or backup code) */
	disable(payload: TOTPDeleteRequest) {
		return HttpClient.delete<FlaskBaseResponse>("/auth/2fa/disable", { data: payload })
	},

	/** Validate 2FA code during login (uses temp_token, no auth header) */
	validate(payload: TOTPValidateRequest) {
		return HttpClient.post<FlaskBaseResponse & TOTPValidateResponse>("/auth/2fa/validate", payload)
	},

	/** Regenerate backup codes (requires TOTP code) */
	regenerateBackupCodes(code: string) {
		return HttpClient.post<FlaskBaseResponse & TOTPBackupCodesResponse>("/auth/2fa/backup-codes/regenerate", {
			code
		})
	}
}
