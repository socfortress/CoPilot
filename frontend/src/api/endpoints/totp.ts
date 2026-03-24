import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export interface TOTPSetupResponse {
	secret: string
	otpauth_url: string
	qr_data_uri: string
	backup_codes: string[]
	message: string
}

export interface TOTPStatusResponse {
	enabled: boolean
	message: string
	success: boolean
}

export interface TOTPBackupCodesResponse {
	backup_codes: string[]
	message: string
	success: boolean
}

export interface TOTPValidateResponse {
	access_token: string
	token_type: string
}

export default {
	/** Get 2FA status for current user */
	getStatus() {
		return HttpClient.get<TOTPStatusResponse>("/auth/2fa/status")
	},

	/** Start 2FA setup — get QR code and backup codes */
	setup() {
		return HttpClient.post<TOTPSetupResponse>("/auth/2fa/setup")
	},

	/** Verify setup with a TOTP code to activate 2FA */
	verifySetup(code: string) {
		return HttpClient.post<FlaskBaseResponse>("/auth/2fa/verify-setup", { code })
	},

	/** Disable 2FA (requires TOTP code or backup code) */
	disable(payload: { code?: string; backup_code?: string }) {
		return HttpClient.delete<FlaskBaseResponse>("/auth/2fa/disable", { data: payload })
	},

	/** Validate 2FA code during login (uses temp_token, no auth header) */
	validate(payload: { temp_token: string; code?: string; backup_code?: string }) {
		return HttpClient.post<TOTPValidateResponse>("/auth/2fa/validate", payload)
	},

	/** Regenerate backup codes (requires TOTP code) */
	regenerateBackupCodes(code: string) {
		return HttpClient.post<TOTPBackupCodesResponse>("/auth/2fa/backup-codes/regenerate", { code })
	}
}
