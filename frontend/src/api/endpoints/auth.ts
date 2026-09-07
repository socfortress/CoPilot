import type { LoginPayload, RegisterPayload } from "@/types/auth"
import type { FlaskBaseResponse } from "@/types/flask"
import jsonToFormData from "@ajoelp/json-to-formdata"
import { HttpClient } from "../http-client"

export default {
	login(payload: LoginPayload) {
		const formData = jsonToFormData(payload)
		return HttpClient.post<
			FlaskBaseResponse & { access_token: string; token_type: string; requires_2fa?: boolean }
		>("/auth/token", formData)
	},
	register(payload: RegisterPayload) {
		return HttpClient.post<FlaskBaseResponse>("/auth/register", payload)
	},
	delete(userId: number) {
		return HttpClient.delete<FlaskBaseResponse>(`/auth/delete/${userId}`)
	},
	refresh() {
		return HttpClient.get<FlaskBaseResponse & { access_token: string; token_type: string }>("/auth/refresh", {
			keepOnNavigation: true
		})
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
	getUserCustomerAccess(userId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { customer_codes: string[] }>(`/auth/users/${userId}/customers`, {
			signal
		})
	},
	/**
	 * Get the current user's accessible customers.
	 *
	 * `scope` says *why* the answer is what it is, which `customer_codes` alone cannot:
	 * `assigned` (scoped to their own customers), `deployment` (admin, always
	 * deployment-wide) or `unassigned` (an analyst nobody assigned a customer to, so
	 * they still see everything). The last one is what makes "I assigned a customer and
	 * the analyst still sees them all" look like a bug rather than a missing assignment.
	 */
	getMyCustomerAccess(signal?: AbortSignal) {
		return HttpClient.get<
			FlaskBaseResponse & { customer_codes: string[]; scope?: "assigned" | "deployment" | "unassigned" }
		>("/auth/me/customers", { signal })
	}
}
