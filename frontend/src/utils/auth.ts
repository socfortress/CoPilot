import { useAuthStore } from "@/stores/auth"
import { type RouteMetaAuth, UserRole } from "@/types/auth.d"
import { type RouteLocationNormalized } from "vue-router"
import _castArray from "lodash/castArray"
import _toNumber from "lodash/toNumber"
import * as jose from "jose"

export function isDebounceTimeOver(lastCheck: Date | null) {
	const TOKEN_DEBOUNCE_TIME = useAuthStore().tokenDebounceTime

	if (!lastCheck) return true

	const timeOver = lastCheck.getTime() + _toNumber(TOKEN_DEBOUNCE_TIME) * 1000
	const now = new Date().getTime()

	return timeOver < now
}

/**
 * @param token jwt token
 * @param threshold in seconds
 */
export function isJwtExpiring(token: string, threshold: number): boolean {
	try {
		if (!token) {
			return false
		}

		const { exp } = jose.decodeJwt(token)
		const now = new Date().getTime() / 1000
		const delta = (exp || 0) - threshold

		if (!exp) {
			return true
		}

		return now > delta && now < exp
	} catch (err) {
		return false
	}
}

export function authCheck(route: RouteLocationNormalized) {
	const meta: RouteMetaAuth = route.meta
	const { checkAuth, authRedirect, auth, roles } = meta

	const authStore = useAuthStore()

	if (route?.redirectedFrom?.name === "Logout") {
		authStore.setLogout()
	}

	if (auth === true) {
		if (!authStore.isLogged) {
			window.location.href = "/login" + window.location.search
			return false
		}

		if (roles && !authStore.isRoleGranted(roles)) {
			window.location.href = "/login" + window.location.search
			return false
		}
	}

	if (checkAuth === true) {
		if (authStore.isLogged) {
			if (roles) {
				if (authStore.isRoleGranted(roles)) {
					return authRedirect || "/"
				} else {
					return route.path
				}
			}
			return authRedirect || "/"
		}
	}
}

export function scopeToRole(scope: string | string[]): UserRole {
	const scopes: string[] = _castArray(scope)
	if (!scopes.length) return UserRole.Unknown

	if (scopes[0].toLowerCase() === "admin") return UserRole.Admin
	if (scopes[0].toLowerCase() === "analyst") return UserRole.Analyst

	return UserRole.Unknown
}
