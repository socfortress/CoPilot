import type { FlaskBaseResponse } from "@/types/flask"
import type { User } from "@/types/user"
import { HttpClient } from "../http-client"

export default {
	getUsers() {
		return HttpClient.get<FlaskBaseResponse & { users: User[] }>("/auth/users")
	},
	getUser(userId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { user: User }>(`/auth/users/${userId}`, { signal })
	}
}
