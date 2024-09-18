import { defineStore, acceptHMRUpdate } from "pinia"
import Api from "@/api"
import { scopeToRole } from "@/utils/auth"
import { getAvatar, getNameInitials } from "@/utils"
import * as jose from "jose"
import _castArray from "lodash/castArray"
import _toLower from "lodash/toLower"
import _toNumber from "lodash/toNumber"
import SecureLS from "secure-ls"
import { UserRole, type User, type LoginPayload } from "@/types/auth.d"
const ls = new SecureLS({ encodingType: "aes", isCompression: false })

export const useAuthStore = defineStore("auth", {
	state: () => ({
		user: {
			access_token: "",
			username: "",
			email: "",
			role: UserRole.Unknown
		} as User,
		tokenDebounceTime: _toNumber(import.meta.env.VITE_TOKEN_DEBOUNCE_TIME) as number // seconds
	}),
	actions: {
		setLogged(token: string) {
			const jwtPayload = jose.decodeJwt(token)
			const scopes = jwtPayload.scopes as string[]

			this.user = {
				access_token: token,
				username: jwtPayload.sub || "",
				email: "",
				role: scopeToRole(scopes)
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
							this.getEmail()
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
		getEmail() {
			Api.auth.getUsers().then(res => {
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
		userRole(state): UserRole {
			return state.user?.role
		},
		userRoleName(state): string {
			return UserRole[(state.user?.role || 0) as number]
		},
		userPic(): string {
			const initial = getNameInitials(this.userName)

			return getAvatar({ seed: initial, text: initial, size: 64 })
		},
		isAdmin(): boolean {
			return _toLower(this.userRoleName) === "admin"
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
		pick: ["user"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
