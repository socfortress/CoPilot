import type { LoginPayload } from "@/api/endpoints/auth"
import type { TOTPValidateRequest } from "@/api/endpoints/totp"
import type { AuthResponse, AuthUser, AuthUserRole, JWTPayload, PortalCustomer, RouteMetaAuthRole } from "@/types/auth"
import type { ApiError } from "@/types/common"
import * as jose from "jose"
import _capitalize from "lodash/capitalize"
import _castArray from "lodash/castArray"
import { acceptHMRUpdate, defineStore } from "pinia"
import Api from "@/api"
import { resetEventSearchMemory } from "@/components/eventSearch/useEventSearchMemory"
import { useAiReportsAvailability } from "@/composables/common/useAiReportsAvailability"
import { useServerNotifications } from "@/composables/common/useServerNotifications"
import { useSlaAvailability } from "@/composables/common/useSlaAvailability"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useReportGenerationStore } from "@/stores/reportGeneration"
import { RouteRole } from "@/types/auth"
import { getAvatar } from "@/utils"
import { jwtRoleToUserRole } from "@/utils/auth"
import { getNameInitials, toNumber } from "@/utils/format"
import { piniaStorage, removePersistentSessionKey } from "@/utils/secure-storage"

export const useAuthStore = defineStore("auth", {
	state: () => ({
		user: null as AuthUser | null,
		/**
		 * The customers from `GET /customer_portal/me`, with names. Until it answers, the
		 * token's `customer_codes` claim stands in (see `accessibleCustomers`).
		 */
		customers: null as PortalCustomer[] | null,
		tokenDebounceTime: toNumber(import.meta.env.VITE_TOKEN_DEBOUNCE_TIME) || 10 // seconds
	}),
	actions: {
		setLogged(payload: AuthResponse) {
			const jwtPayload = jose.decodeJwt<JWTPayload>(payload.access_token)

			this.user = {
				access_token: payload.access_token,
				username: jwtPayload.sub || "",
				customer_codes: jwtPayload.customer_codes ?? [],
				role: jwtRoleToUserRole(jwtPayload.scopes),
				must_change_password: !!payload.must_change_password
			}
			// A new session: never show the customers of the previous one.
			this.customers = null
		},
		/**
		 * Hold the user on the password change, or let them go (#1277). Set from the login,
		 * the profile, or any request the API refuses for that reason; cleared by the change.
		 */
		setPasswordChangeRequired(value: boolean) {
			if (this.user) {
				this.user.must_change_password = value
			}
		},
		setTokens(payload: AuthResponse) {
			if (this.user) {
				this.user.access_token = payload.access_token
			}
		},
		setLogout() {
			this.user = null
			this.customers = null

			useCustomerFilterStore().clear()
			useReportGenerationStore().reset()
			// The next user may see other customers, whose AI report and SLA switches may
			// be off: neither cached answer may outlive the session that asked.
			useAiReportsAvailability().reset()
			useSlaAvailability().reset()
			// The bell's server notifications are the user's own (#1282).
			useServerNotifications().reset()
			// Event search's saved and recent searches are the user's own (#1258).
			resetEventSearchMemory()
			removePersistentSessionKey()
		},
		async login(payload: LoginPayload) {
			try {
				const response = await Api.auth.login(payload)

				// When 2FA is enabled the response carries a short-lived temp token and
				// `requires_2fa: true`. Do NOT treat it as a session — the caller hands the
				// temp token to the 2FA challenge and completes login via verify2fa().
				if (response.data && !response.data.requires_2fa) {
					this.setLogged(response.data)
				}

				return response.data
			} catch (err) {
				const error = err as ApiError
				throw error.response?.data
			}
		},
		async verify2fa(payload: TOTPValidateRequest) {
			try {
				const response = await Api.totp.validate(payload)

				if (response.data) {
					this.setLogged(response.data)
				}

				return response.data
			} catch (err) {
				const error = err as ApiError
				throw error.response?.data
			}
		},
		/**
		 * Load the user's customers, with names. Read live: an assignment changed after
		 * login shows here, while the token keeps the codes it was issued with. A failure
		 * keeps what is known (the token's codes, or the last answer): names are a
		 * nicety, never a reason to block the portal.
		 */
		async loadProfile() {
			if (!this.isLogged) return
			try {
				const response = await Api.portal.me()
				if (response.data?.success && this.isLogged) {
					this.customers = response.data.customers
					// Read live, like the customers: an admin may have set a password since login.
					this.setPasswordChangeRequired(!!response.data.must_change_password)
				}
			} catch (err) {
				console.error("Failed to load the portal profile:", err)
			}
		},
		/** Extend the session by re-issuing the access token. Rejects with the API error body. */
		async refreshToken(): Promise<AuthResponse> {
			try {
				const response = await Api.auth.refresh()
				if (!response.data?.access_token) {
					throw new Error("Empty refresh response")
				}
				this.setTokens(response.data)
				return response.data
			} catch (err) {
				const error = err as ApiError
				throw error.response?.data || err
			}
		}
	},
	getters: {
		isLogged(state): boolean {
			return !!state.user?.access_token
		},
		userToken(state): string | null {
			return state.user?.access_token || null
		},
		/** The user must replace a password an admin chose before using the portal (#1277). */
		mustChangePassword(state): boolean {
			return !!state.user?.must_change_password
		},
		/** The customers the user may see, named once the profile has loaded. */
		accessibleCustomers(state): PortalCustomer[] {
			if (state.customers) return state.customers
			return (state.user?.customer_codes ?? []).map(code => ({ customer_code: code, customer_name: code }))
		},
		accessibleCustomerCodes(): string[] {
			return this.accessibleCustomers.map(customer => customer.customer_code)
		},
		/** A customer's name, or its code when the name is not known (e.g. not one of the user's). */
		customerName() {
			return (code: string | null | undefined): string => {
				if (!code) return ""
				return this.accessibleCustomers.find(customer => customer.customer_code === code)?.customer_name || code
			}
		},
		userName(state): string | null {
			return state.user?.username || null
		},
		userRole(state): AuthUserRole | string | null {
			return state.user?.role || null
		},
		userRoleName(state): string | null {
			return _capitalize(state.user?.role ?? "")
		},
		userPic(): string {
			const initial = getNameInitials(this.userName || "")

			return getAvatar({ seed: initial, text: initial, size: 64 })
		},
		isRoleGranted() {
			return (roles?: RouteMetaAuthRole | RouteMetaAuthRole[]) => {
				if (!roles) {
					return true
				}
				if (!this.userRole) {
					return false
				}

				const arrRoles: RouteMetaAuthRole[] = _castArray(roles)

				if (arrRoles.includes(RouteRole.All)) {
					return true
				}

				return arrRoles.includes(this.userRole)
			}
		}
	},
	persist: {
		storage: piniaStorage({ session: true }),
		pick: ["user", "customers"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
