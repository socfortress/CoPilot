import type { FlaskBaseResponse } from "@/types/flask"
import type { CustomerSecurityUser } from "@/types/security"
import { HttpClient } from "../http-client"

export default {
	/** List the user accounts scoped to a customer, with TOTP + last-login status (admin) */
	listCustomerUsers(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { users: CustomerSecurityUser[] }>(
			`/auth/security/customers/${customerCode}/users`,
			{ signal }
		)
	},

	/** Whether SMTP is configured (enables the temporary-password email action) */
	getSmtpStatus() {
		return HttpClient.get<FlaskBaseResponse & { configured: boolean }>(`/auth/security/smtp-status`)
	},

	/** Force-reset a user's TOTP (2FA) without requiring their code (admin) */
	forceResetTotp(userId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/auth/security/users/${userId}/totp`)
	},

	/** Generate a temporary password, set it, and email it to the user (admin) */
	sendTempPassword(userId: number) {
		return HttpClient.post<FlaskBaseResponse>(`/auth/security/users/${userId}/send-temp-password`)
	}
}
