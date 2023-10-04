import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { LoginPayload, RegisterPayload } from "@/types/auth.d"

export default {
	login(payload: LoginPayload) {
		return HttpClient.post<FlaskBaseResponse & { token: string }>("/auth/login", payload)
	},
	register(payload: RegisterPayload) {
		return HttpClient.post<FlaskBaseResponse>("/auth/register", payload)
	},
	refresh() {
		return HttpClient.get<FlaskBaseResponse & { token: string }>("/refresh")
	}
}
