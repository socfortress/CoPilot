import type { FlaskBaseResponse } from "@/types/flask"
import type { User } from "@/types/user"
import { HttpClient } from "../httpClient"

export default {
	getUsers() {
		return HttpClient.get<FlaskBaseResponse & { users: User[] }>("/auth/users")
	}
}
