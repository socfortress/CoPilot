import type { AuthResponse } from "@/types/auth"
import type { CommonResponse } from "@/types/common"
import { HttpClient } from "../httpClient"

export interface LoginPayload {
	username: string
	password: string
}

export default {
	/** Authenticate user with local username/password */
	login(payload: LoginPayload) {
		return HttpClient.postForm<CommonResponse<AuthResponse>>("/auth/token/customer-portal", payload)
	},

	/**
	 * Re-issue the access token while the current one is still valid (sliding expiry).
	 * The bearer header is attached by the request interceptor; the backend re-emits the
	 * `customer_codes` claim for customer_user accounts.
	 */
	refresh() {
		return HttpClient.get<AuthResponse>("/auth/refresh")
	},

	resetPassword(username: string, newPassword: string, currentPassword: string) {
		return HttpClient.post<CommonResponse>("/auth/reset-password/me", {
			username,
			current_password: currentPassword,
			new_password: newPassword
		})
	}
}
