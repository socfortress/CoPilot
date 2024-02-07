import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { AuthUser, LoginPayload, RegisterPayload } from "@/types/auth.d"
import jsonToFormData from "@ajoelp/json-to-formdata"

export default {
	login(payload: LoginPayload) {
		const formData = jsonToFormData(payload)
		return HttpClient.post<FlaskBaseResponse & { access_token: string; token_type: string }>(
			"/auth/token",
			formData
		)
	},
	register(payload: RegisterPayload) {
		return HttpClient.post<FlaskBaseResponse>("/auth/register", payload)
	},
	refresh() {
		return HttpClient.get<FlaskBaseResponse & { access_token: string; token_type: string }>("/auth/refresh")
	},
	getUsers() {
		return HttpClient.get<FlaskBaseResponse & { users: AuthUser[] }>("/auth/users")
	},
	/** need admin role */
	resetPassword(username: string, password: string) {
		return HttpClient.post<FlaskBaseResponse>("/auth/reset-password", {
			username,
			new_password: password
		})
	},
	resetOwnPassword(username: string, password: string) {
		return HttpClient.post<FlaskBaseResponse>("/auth/reset-password/me", {
			username,
			new_password: password
		})
	}
}
