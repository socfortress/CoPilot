import type { LoginPayload, RegisterPayload } from "@/types/auth.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import jsonToFormData from "@ajoelp/json-to-formdata"
import { HttpClient } from "../httpClient"

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
	delete(userId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/auth/delete/${userId}`)
	},
	refresh() {
		return HttpClient.get<FlaskBaseResponse & { access_token: string; token_type: string }>("/auth/refresh")
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
