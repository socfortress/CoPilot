import type { AuthResponse } from "@/types/auth"
import { HttpClient } from "../httpClient"

export interface LoginPayload {
	username: string
	password: string
}

export default {
	/** Authenticate user with local username/password */
	login(payload: LoginPayload) {
		return HttpClient.postForm<AuthResponse>("/auth/token/customer-portal", payload)
	},

	/** Refresh access token using the application refresh token (non-Keycloak) */
	refresh(refreshToken: string) {
		return HttpClient.post<AuthResponse>("/auth/refresh", { refresh_token: refreshToken })
	}
}
