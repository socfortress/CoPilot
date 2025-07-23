import type { AuthUser, JWTPayload, LoginPayload, RouteMetaAuthRole } from "@/types/auth.d"
import type { ApiError } from "@/types/common.d"
import * as jose from "jose"
import _castArray from "lodash/castArray"
import _toLower from "lodash/toLower"
import _toNumber from "lodash/toNumber"
import { acceptHMRUpdate, defineStore } from "pinia"
import Api from "@/api"
import { AuthUserRole, RouteRole } from "@/types/auth.d"
import { getAvatar, getNameInitials } from "@/utils"
import { jwtRoleToUserRole } from "@/utils/auth"
import { piniaStorage, removePersistentSessionKey } from "@/utils/secure-storage"

export const useAuthStore = defineStore("auth", {
	state: () => ({
		user: {
			access_token: "",
			username: "",
			email: "",
			role: AuthUserRole.Unknown
		} as AuthUser,
		tokenDebounceTime: _toNumber(import.meta.env.VITE_TOKEN_DEBOUNCE_TIME) as number // seconds
	}),
	actions: {
		setLogged(token: string) {
			const jwtPayload = jose.decodeJwt<JWTPayload>(token)
			const scopes = jwtPayload.scopes

			this.user = {
				access_token: token,
				username: jwtPayload.sub || "",
				email: "",
				role: jwtRoleToUserRole(scopes)
			}
		},
		setToken(token: string) {
			this.user.access_token = token
		},
		setLogout() {
			this.user = {
				access_token: "",
				username: "",
				email: "",
				role: AuthUserRole.Unknown
			}

			removePersistentSessionKey()
		},
		async login(payload: LoginPayload) {
			try {
				const response = await Api.auth.login(payload)

				if (response.data.access_token) {
					this.setLogged(response.data.access_token)
					this.getEmail()
				}

				return response.data
			} catch (err) {
				const error = err as ApiError
				throw error.response?.data
			}
		},
		getEmail() {
			Api.users.getUsers().then(res => {
				if (res.data.users) {
					const user = res.data.users.find(o => o.username === this.userName)
					this.user.email = user?.email || ""
				}
			})
		},
		refreshToken() {
			return new Promise((resolve, reject) => {
				Api.auth
					.refresh()
					.then(res => {
						if (res.data.access_token) {
							this.setToken(res.data.access_token)
							resolve(res.data)
						} else {
							reject(res.data)
						}
					})
					.catch(err => {
						reject(err.response?.data)
					})
			})
		}
	},
	getters: {
		isLogged(state): boolean {
			return !!state.user?.access_token
		},
		userToken(state): string {
			return state.user?.access_token
		},
		userName(state): string {
			return state.user?.username
		},
		userEmail(state): string {
			return state.user?.email
		},
		userRole(state): AuthUserRole {
			return state.user?.role
		},
		userRoleName(state): string {
			return AuthUserRole[(state.user?.role || 0) as number]
		},
		userPic(): string {
			const initial = getNameInitials(this.userName)

			return getAvatar({ seed: initial, text: initial, size: 64 })
		},
		isAdmin(): boolean {
			return _toLower(this.userRoleName) === "admin"
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
