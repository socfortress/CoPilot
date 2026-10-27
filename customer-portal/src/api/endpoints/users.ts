import type { CommonResponse } from "@/types/common"
import type { InvitePayload, TemporaryPasswordDelivery, TenantUserAction, TenantUsers } from "@/types/users"
import { HttpClient } from "../httpClient"

/** A customer admin's management of their customers' portal users (#1296). */
export default {
	list(signal?: AbortSignal) {
		return HttpClient.get<CommonResponse<TenantUsers>>("/customer_portal/users", { signal })
	},

	/** Invite a portal user; the temporary password is emailed, or in the answer to be shown once. */
	invite(payload: InvitePayload) {
		return HttpClient.post<CommonResponse<TenantUserAction & TemporaryPasswordDelivery>>(
			"/customer_portal/users",
			payload
		)
	},

	disable(userId: number) {
		return HttpClient.post<CommonResponse<TenantUserAction>>(`/customer_portal/users/${userId}/disable`)
	},

	enable(userId: number) {
		return HttpClient.post<CommonResponse<TenantUserAction>>(`/customer_portal/users/${userId}/enable`)
	},

	/** Let a user only read the data of the customers they share with the caller, or change it again (#1312). */
	setReadOnly(userId: number, readOnly: boolean) {
		return HttpClient.put<CommonResponse<TenantUserAction>>(`/customer_portal/users/${userId}/read-only`, {
			read_only: readOnly
		})
	},

	resetTotp(userId: number) {
		return HttpClient.delete<CommonResponse<TenantUserAction>>(`/customer_portal/users/${userId}/totp`)
	},

	/** A new temporary password, emailed or in the answer to be shown once; the user replaces it. */
	issueTemporaryPassword(userId: number) {
		return HttpClient.post<CommonResponse<TenantUserAction & TemporaryPasswordDelivery>>(
			`/customer_portal/users/${userId}/temporary-password`
		)
	}
}
