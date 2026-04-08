import type { LoginPayload } from "@/api/endpoints/auth"
import type { AuthResponse, AuthUser, AuthUserRole, JWTPayload, RouteMetaAuthRole } from "@/types/auth"
import type { ApiError } from "@/types/common"
import * as jose from "jose"
import _capitalize from "lodash/capitalize"
import _castArray from "lodash/castArray"
import { acceptHMRUpdate, defineStore } from "pinia"
import Api from "@/api"
import { RouteRole } from "@/types/auth"
import { getAvatar } from "@/utils"
import { jwtRoleToUserRole } from "@/utils/auth"
import { getNameInitials, toNumber } from "@/utils/format"
import { piniaStorage, removePersistentSessionKey } from "@/utils/secure-storage"

export const useAuthStore = defineStore("auth", {
	state: () => ({
		user: null as AuthUser | null,
		tokenDebounceTime: toNumber(import.meta.env.VITE_TOKEN_DEBOUNCE_TIME) || 10 // seconds
	}),
	actions: {
		setLogged(payload: AuthResponse) {
			const jwtPayload = jose.decodeJwt<JWTPayload>(payload.access_token)

			this.user = {
				access_token: payload.access_token,
				refresh_token: payload.refresh_token,
				username: jwtPayload.sub || "",
				customer_code: jwtPayload.customer_codes?.[0] || null,
				role: jwtRoleToUserRole(jwtPayload.scopes)
			}
		},
		setTokens(payload: AuthResponse) {
			if (this.user) {
				this.user.access_token = payload.access_token
				this.user.refresh_token = payload.refresh_token
			}
		},
		setLogout() {
			this.user = null

			removePersistentSessionKey()
		},
		async login(payload: LoginPayload) {
			try {
				const response = await Api.auth.login(payload)

				if (response.data) {
					this.setLogged(response.data)
				}

				return response.data
			} catch (err) {
				const error = err as ApiError
				throw error.response?.data
			}
		},
		refreshToken() {
			return new Promise((resolve, reject) => {
				const refreshToken = this.user?.refresh_token || ""

				Api.auth
					.refresh(refreshToken)
					.then(res => {
						if (res.data) {
							this.setTokens(res.data)
							resolve(res.data)
						} else {
							reject(res.data)
						}
					})
					.catch(err => {
						reject(err.response?.data || err)
					})
			})
		}
	},
	getters: {
		isLogged(state): boolean {
			return !!state.user?.access_token
		},
		userToken(state): string | null {
			return state.user?.access_token || null
		},
		userCustomerCode(state): string | null {
			return state.user?.customer_code || null
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
		pick: ["user"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
