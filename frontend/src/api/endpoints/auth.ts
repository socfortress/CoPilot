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
	},
	/** need admin role */
	assignRole(userId: number, roleName: string) {
		return HttpClient.put<FlaskBaseResponse>(`/auth/users/${userId}/role/by-name`, {
			role_name: roleName
		})
	},
	/** need admin role */
	assignCustomerAccess(userId: number, customerCodes: string[]) {
		return HttpClient.post<FlaskBaseResponse>(`/auth/users/${userId}/customers`, customerCodes)
	},
	/** need admin role */
	getUserCustomerAccess(userId: number) {
		return HttpClient.get<FlaskBaseResponse & { customer_codes: string[] }>(`/auth/users/${userId}/customers`)
	},
	/** get current user's accessible customers */
	getMyCustomerAccess() {
		return HttpClient.get<FlaskBaseResponse & { customer_codes: string[] }>("/auth/me/customers")
	}
}
