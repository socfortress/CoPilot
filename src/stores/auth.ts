import { defineStore, acceptHMRUpdate } from "pinia"
import type { Role, Roles, User } from "@/types/auth.d"
import _castArray from "lodash/castArray"

export const useAuthStore = defineStore("auth", {
	state: () => ({
		logged: true,
		role: "admin" as Role | null,
		user: {
			token: ""
		} as User
	}),
	actions: {
		setLogged(payload: User) {
			this.logged = true
			this.role = "admin"
			this.user = payload
		},
		// TODO: save crypted
		setToken(token: string) {
			this.user.token = token
		},
		setLogout() {
			this.logged = false
			this.role = null
			this.user = {
				token: ""
			}
		}
	},
	getters: {
		isLogged(state) {
			return state.logged
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
		paths: ["logged", "role", "user"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
