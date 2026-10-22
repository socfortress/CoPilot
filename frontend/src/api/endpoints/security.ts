import type { FlaskBaseResponse } from "@/types/flask"
import type { CustomerSecurityUser, TempPasswordEmailOptions, TempPasswordEmailPreview } from "@/types/security"
import { HttpClient } from "../http-client"

export interface TempPasswordEmailOptionsQuery {
	userId: number
	customerCode?: string | null
}

export default {
	/** List the user accounts scoped to a customer, with TOTP + last-login status (admin) */
	listCustomerUsers(customerCode: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { users: CustomerSecurityUser[] }>(
			`/auth/security/customers/${customerCode}/users`,
			{ signal }
		)
	},

	/** Whether SMTP is configured (enables the temporary-password email action) */
	getSmtpStatus(signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { configured: boolean }>(`/auth/security/smtp-status`, { signal })
	},

	/** Force-reset a user's TOTP (2FA) without requiring their code (admin) */
	forceResetTotp(userId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/auth/security/users/${userId}/totp`)
	},

	/**
	 * Which temporary-password templates can serve this user, best match first,
	 * and which one a send with no override would pick (admin).
	 */
	getTempPasswordEmailOptions({ userId, customerCode }: TempPasswordEmailOptionsQuery, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & TempPasswordEmailOptions>(
			`/auth/security/users/${userId}/temp-password-email/options`,
			{ params: customerCode ? { customer_code: customerCode } : {}, signal }
		)
	},

	/**
	 * Render the email as this user would receive it, with a placeholder password.
	 * Nothing is sent and no password is rotated (admin).
	 */
	previewTempPasswordEmail(userId: number, payload: { template_id?: number | null; customer_code?: string | null }) {
		return HttpClient.post<FlaskBaseResponse & TempPasswordEmailPreview>(
			`/auth/security/users/${userId}/temp-password-email/preview`,
			payload
		)
	},

	/**
	 * Generate a temporary password, set it, and email it to the user (admin).
	 * Omitting `template_id` lets the backend resolve one by scope.
	 */
	sendTempPassword(userId: number, payload?: { template_id?: number | null; customer_code?: string | null }) {
		return HttpClient.post<FlaskBaseResponse>(`/auth/security/users/${userId}/send-temp-password`, payload ?? {})
	},

	/** Make a portal user an administrator of this customer's portal users, or not (admin, #1296) */
	setCustomerAdmin(customerCode: string, userId: number, isCustomerAdmin: boolean) {
		return HttpClient.put<FlaskBaseResponse>(
			`/auth/security/customers/${customerCode}/users/${userId}/customer-admin`,
			{
				is_customer_admin: isCustomerAdmin
			}
		)
	},

	/** Disable a portal user: no sign-in, and a session they hold ends (admin, #1296) */
	disableUser(userId: number) {
		return HttpClient.post<FlaskBaseResponse>(`/auth/security/users/${userId}/disable`)
	},

	/** Enable a disabled portal user again (admin, #1296) */
	enableUser(userId: number) {
		return HttpClient.post<FlaskBaseResponse>(`/auth/security/users/${userId}/enable`)
	}
}
