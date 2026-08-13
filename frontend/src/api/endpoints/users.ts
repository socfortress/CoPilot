import type { FlaskBaseResponse } from "@/types/flask"
import type { User } from "@/types/user"
import { HttpClient } from "../http-client"
import { searchLimitParams } from "../params"

export default {
	getUsers(query: { search?: string; limit?: number } = {}, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { users: User[] }>("/auth/users", {
			params: searchLimitParams(query),
			signal
		})
	},
	getUser(userId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { user: User }>(`/auth/users/${userId}`, { signal })
	}
}
