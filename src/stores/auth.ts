import { defineStore, acceptHMRUpdate } from "pinia"
import { UserRole, type User, type LoginPayload } from "@/types/auth.d"
import _castArray from "lodash/castArray"
import Api from "@/api"
import * as jose from "jose"
import SecureLS from "secure-ls"
import { scopeToRole } from "@/utils/auth"
const ls = new SecureLS({ encodingType: "aes", isCompression: false })

export const useAuthStore = defineStore("auth", {
	state: () => ({
		user: {
			access_token: "",
			role: UserRole.Unknown
		} as User
	}),
	actions: {
		setLogged(token: string) {
			const jwtPayload = jose.decodeJwt(token)
			const scopes = jwtPayload.scopes as string[]

			this.user = {
				access_token: token,
				role: scopeToRole(scopes)
			}
		},
		setToken(token: string) {
			this.user.access_token = token
		},
		setLogout() {
			this.user = {
				access_token: "",
				role: UserRole.Unknown
			}
		},
		login(payload: LoginPayload) {
			return new Promise((resolve, reject) => {
				Api.auth
					.login(payload)
					.then(res => {
						if (res.data.access_token) {
							this.setLogged(res.data.access_token)
							resolve(res.data)
						} else {
							reject(res.data)
						}
					})
					.catch(err => {
						reject(err.response?.data)
					})
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
		userRole(state): UserRole {
			return state.user?.role
		},
		userRoleName(state): string {
			return UserRole[(state.user?.role || 0) as number]
		},
		isRoleGranted() {
			return (roles?: UserRole | UserRole[]) => {
				if (!roles) {
					return true
				}
				if (!this.userRole) {
					return false
				}

				const arrRoles: UserRole[] = _castArray(roles)

				if (arrRoles.includes(UserRole.All)) {
					return true
				}

				return arrRoles.includes(this.userRole)
			}
		}
	},
	persist: {
		storage: {
			getItem: key => ls.get(key),
			setItem: (key, value) => ls.set(key, value)
		},
		paths: ["user"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
