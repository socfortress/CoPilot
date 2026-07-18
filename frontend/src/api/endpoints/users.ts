import type { FlaskBaseResponse } from "@/types/flask"
import type { User } from "@/types/user"
import { HttpClient } from "../http-client"

export default {
	getUsers(query: { search?: string; limit?: number } = {}, signal?: AbortSignal) {
		const params: Record<string, number | string> = {}
		if (query.search) params.search = query.search
		if (query.limit !== undefined) params.limit = query.limit

		return HttpClient.get<FlaskBaseResponse & { users: User[] }>("/auth/users", { params, signal })
	},
	getUser(userId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { user: User }>(`/auth/users/${userId}`, { signal })
	}
}
