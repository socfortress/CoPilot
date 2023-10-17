import { useAuthStore } from "@/stores/auth"
import { type RouteMetaAuth, UserRole } from "@/types/auth.d"
import { type RouteLocationNormalized } from "vue-router"
import _castArray from "lodash/castArray"
import _toNumber from "lodash/toNumber"
import * as jose from "jose"

const TOKEN_DEBOUNCE_TIME = import.meta.env.VITE_TOKEN_DEBOUNCE_TIME // seconds

export function isDebounceTimeOver(lastCheck: Date | null) {
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

	if (route?.redirectedFrom?.name === "Logout") {
		useAuthStore().setLogout()
	}

	if (auth === true) {
		if (!useAuthStore().isLogged) {
			window.location.href = "/login" + window.location.search
			return false
		}

		if (roles && !useAuthStore().isRoleGranted(roles)) {
			window.location.href = "/login" + window.location.search
			return false
		}
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
}

export function scopeToRole(scope: string | string[]): UserRole {
	const scopes: string[] = _castArray(scope)
	if (!scopes.length) return UserRole.Unknown

	if (scopes[0].toLowerCase() === "admin") return UserRole.Admin
	if (scopes[0].toLowerCase() === "analyst") return UserRole.Analyst

	return UserRole.Unknown
}
