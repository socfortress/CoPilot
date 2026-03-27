import type { AuthResponse } from "@/types/auth"
import type { CommonResponse } from "@/types/common"
import type { User } from "@/types/user"
import { HttpClient } from "../httpClient"

export interface LoginPayload {
	username: string
	password: string
}

export default {
	/** Authenticate user with local username/password */
	login(payload: LoginPayload) {
		return HttpClient.postForm<AuthResponse>("/auth/login", payload)
	},

	/** Refresh access token using the application refresh token (non-Keycloak) */
	refresh(refreshToken: string) {
		return HttpClient.post<AuthResponse>("/auth/refresh", { refresh_token: refreshToken })
	},

	/** Get Keycloak authorization URL to start OIDC login */
	getKeycloakLoginUrl(redirectUri: string) {
		return HttpClient.get<{ auth_url: string; message: string }>("/auth/keycloak/login", {
			params: { redirect_uri: redirectUri }
		})
	},

	/** Exchange Keycloak authorization code for access/refresh tokens */
	exchangeKeycloakCode(code: string, redirectUri: string) {
		return HttpClient.post<AuthResponse>("/auth/keycloak/callback", null, {
			params: { code, redirect_uri: redirectUri }
		})
	},

	/** Refresh access token using Keycloak refresh token */
	refreshKeycloakToken(refreshToken: string) {
		return HttpClient.post<AuthResponse>("/auth/keycloak/refresh", {
			refresh_token: refreshToken
		})
	},

	/** Logout from Keycloak invalidating the refresh token */
	logoutKeycloak(refreshToken: string) {
		return HttpClient.post<{ message: string }>("/auth/keycloak/logout", null, {
			params: { refresh_token: refreshToken }
		})
	},

	/** Get authenticated user profile */
	getProfile() {
		return HttpClient.get<CommonResponse<{ user: User }>>("/auth/me")
	},

	/** Delete user by ID */
	delete(userId: number) {
		return HttpClient.delete(`/auth/delete/${userId}`)
	}
}
