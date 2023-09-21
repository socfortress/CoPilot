import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { LoginPayload, RegisterPayload } from "@/types/auth.d"

export default {
	login(payload: LoginPayload) {
		return HttpClient.post<FlaskBaseResponse>("/login", payload)
	},
	register(payload: RegisterPayload) {
		return HttpClient.post<FlaskBaseResponse>("/register", payload)
	},
	refresh() {
		return HttpClient.get<FlaskBaseResponse>("/refresh")
	}
}
