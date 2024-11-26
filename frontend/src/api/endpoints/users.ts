import type { FlaskBaseResponse } from "@/types/flask.d"
import type { User } from "@/types/user.d"
import { HttpClient } from "../httpClient"

export default {
	getUsers() {
		return HttpClient.get<FlaskBaseResponse & { users: User[] }>("/auth/users")
	}
}
