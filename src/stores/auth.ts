import { defineStore, acceptHMRUpdate } from "pinia"
import type { Role, Roles } from "@/types/auth.d"
import _castArray from "lodash/castArray"

// HERE YOU CAN IMPLEMENT YOUR LOGIN

export const useAuthStore = defineStore("auth", {
	state: () => ({
		logged: true,
		role: "admin" as Role | null,
		user: {}
	}),
	actions: {
		setLogged(payload?: any) {
			this.logged = true
			this.role = "admin"
			this.user = payload
		},
		setLogout() {
			this.logged = false
			this.role = null
			this.user = {}
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
		paths: ["logged", "role"]
	}
})

if (import.meta.hot) {
	import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
