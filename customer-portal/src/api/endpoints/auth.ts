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

	/** Refresh access token using the application refresh token (non-Keycloak) */
	refresh(refreshToken: string) {
		return HttpClient.post<CommonResponse<AuthResponse>>("/auth/refresh", { refresh_token: refreshToken })
	},

	resetPassword(username: string, newPassword: string, currentPassword: string) {
		return HttpClient.post<CommonResponse>("/auth/reset-password/me", {
			username,
			current_password: currentPassword,
			new_password: newPassword
		})
	}
}
