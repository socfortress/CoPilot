import { defineStore, acceptHMRUpdate } from "pinia"
import type { Role, Roles, User } from "@/types/auth.d"
import _castArray from "lodash/castArray"
import SecureLS from "secure-ls"
const ls = new SecureLS({ encodingType: "aes", isCompression: false })

export const useAuthStore = defineStore("auth", {
	state: () => ({
		role: "admin" as Role | null,
		user: {
			token: ""
		} as User
	}),
	actions: {
		setLogged(payload: User) {
			this.role = "admin"
			this.user = payload
		},
		setToken(token: string) {
			this.user.token = token
		},
		setLogout() {
			this.role = null
			this.user = {
				token: ""
			}
		}
	},
	getters: {
		isLogged(state) {
			return state.user?.token
		},
		userRole(state) {
			return state.role
		},
		isRoleGranted(state) {
			return (roles?: Roles) => {
				if (!roles) {
					return true
				}
				if (!state.role) {
					return false
				}

				const arrRoles: Role[] = _castArray(roles)

				if (arrRoles.includes("all")) {
					return true
				}

				return arrRoles.includes(state.role)
			}
		}
	},
	persist: {
		storage: {
			getItem: key => ls.get(key),
			setItem: (key, value) => ls.set(key, value)
		},
		paths: ["role", "user"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
