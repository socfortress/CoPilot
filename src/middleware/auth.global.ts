import { useAuthStore } from "@/stores/auth"
import { type RouteMetaAuth } from "@/types/auth.d"
import { type RouteLocationNormalized } from "vue-router"

export function authCheck(route: RouteLocationNormalized) {
	const meta: RouteMetaAuth = route.meta
	const { checkAuth, authRedirect, auth, roles } = meta

	if (route?.redirectedFrom?.name === "logout") {
		useAuthStore().setLogout()
	}

	if (checkAuth === true) {
		if (useAuthStore().isLogged) {
			if (roles) {
				if (useAuthStore().isRoleGranted(roles)) {
					return authRedirect || "/"
				} else {
					return route.path
				}
			}
			return authRedirect || "/"
		}
	}

	if (auth === true) {
		if (!useAuthStore().isLogged) {
			return "/login"
		}

		if (roles && !useAuthStore().isRoleGranted(roles)) {
			return "/login"
		}
	}
}
