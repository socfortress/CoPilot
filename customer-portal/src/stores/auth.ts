import type { LoginPayload } from "@/api/endpoints/auth"
import type { AuthResponse, AuthUser, JWTPayload, RouteMetaAuthRole } from "@/types/auth"
import type { ApiError } from "@/types/common"
import type { User } from "@/types/user"
import * as jose from "jose"
import _capitalize from "lodash/capitalize"
import _castArray from "lodash/castArray"
import _toLower from "lodash/toLower"
import { acceptHMRUpdate, defineStore } from "pinia"
import Api from "@/api"
import { AuthUserRole, RouteRole } from "@/types/auth"
import { getAvatar } from "@/utils"
import { jwtRoleToUserRole } from "@/utils/auth"
import { getNameInitials, toBoolean, toNumber } from "@/utils/format"
import { piniaStorage, removePersistentSessionKey } from "@/utils/secure-storage"

export const useAuthStore = defineStore("auth", {
	state: () => ({
		user: null as AuthUser | null,
		profile: null as User | null,
		loadingProfile: false,
		tokenDebounceTime: toNumber(import.meta.env.VITE_TOKEN_DEBOUNCE_TIME) || 10, // seconds
		useCustomAuth: toBoolean(import.meta.env.VITE_USE_CUSTOM_AUTH) || false,
		useKeycloak: !toBoolean(import.meta.env.VITE_USE_CUSTOM_AUTH),
		keycloakCallbackUrl: `${window.location.origin}${import.meta.env.VITE_KEYCLOAK_CALLBACK_URL || "/auth/callback"}`
	}),
	actions: {
		setLogged(payload: AuthResponse) {
			const jwtPayload = jose.decodeJwt<JWTPayload>(payload.access_token)

			this.user = {
				access_token: payload.access_token,
				refresh_token: payload.refresh_token,
				username: jwtPayload.preferred_username || "",
				role: jwtRoleToUserRole(jwtPayload.user_role)
			}
		},
		setTokens(payload: AuthResponse) {
			if (this.user) {
				this.user.access_token = payload.access_token
				this.user.refresh_token = payload.refresh_token
			}
		},
		setProfile(payload: User) {
			this.profile = payload
		},
		setLogout() {
			if (this.useKeycloak) {
				const refreshToken = this.user?.refresh_token
				if (refreshToken) {
					Api.auth.logoutKeycloak(refreshToken).catch(() => {})
				}
			}

			this.user = null
			this.profile = null

			removePersistentSessionKey()
		},
		/** used if USE_CUSTOM_AUTH is true */
		async login(payload: LoginPayload) {
			try {
				const response = await Api.auth.login(payload)

				if (response.data) {
					this.setLogged(response.data)
					this.loadProfile()
				}

				return response.data
			} catch (err) {
				const error = err as ApiError
				throw error.response?.data
			}
		},
		async loadProfile(): Promise<User | null> {
			if (this.profile) {
				return this.profile
			}

			if (this.loadingProfile) {
				return null
			}

			if (!this.isLogged) {
				return null
			}

			this.loadingProfile = true

			try {
				const response = await Api.auth.getProfile()
				this.setProfile(response.data.user)
				return response.data.user || null
			} catch (err) {
				const error = err as ApiError
				throw error.response?.data || error
			} finally {
				this.loadingProfile = false
			}
		},
		refreshToken() {
			return new Promise((resolve, reject) => {
				const refreshToken = this.user?.refresh_token || ""

				const refreshMethod = this.useKeycloak ? Api.auth.refreshKeycloakToken : Api.auth.refresh

				refreshMethod(refreshToken)
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
		userName(state): string | null {
			return state.user?.username || null
		},
		userFullName(state): string | null {
			return state.profile?.full_name || null
		},
		userEmail(state): string | null {
			return state.profile?.email || null
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
		userCustomerId(): number | null {
			return this.profile?.customer_id || null
		},
		isAdmin(): boolean {
			return !!(this.userRoleName && _toLower(this.userRoleName) === "admin")
		},
		isSuperuser(): boolean {
			return this.userRole === AuthUserRole.Superuser
		},
		isMSSPUser(): boolean {
			return this.userCustomerId === null && !this.isSuperuser
		},
		isRegularUser(): boolean {
			return !this.isSuperuser && this.userCustomerId !== null
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
		pick: ["user", "profile"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
