import type { RouteLocationNormalized } from "vue-router"
import { useAuthStore } from "@/stores/auth"
import { type RouteMetaAuth, UserRole } from "@/types/auth.d"
import { decodeJwt } from "jose"
import _castArray from "lodash/castArray"
import _toNumber from "lodash/toNumber"

export function isDebounceTimeOver(lastCheck: Date | null) {
	const debounceTime = useAuthStore().tokenDebounceTime
	return !lastCheck || lastCheck.getTime() + _toNumber(debounceTime) * 1000 < Date.now()
}

/**
 * @param token jwt token
 * @param threshold in seconds
 */
export function isJwtExpiring(token: string, threshold: number): boolean {
	try {
		const { exp } = decodeJwt(token) || {}
		return exp ? Date.now() / 1000 > exp - threshold : true
	} catch {
		return false
	}
}

export function authCheck(route: RouteLocationNormalized) {
	const { checkAuth, authRedirect, auth, roles }: RouteMetaAuth = route.meta
	const authStore = useAuthStore()

	if (route?.redirectedFrom?.name === "Logout") authStore.setLogout()

	if (auth && !authStore.isLogged) {
		window.location.href = `/login${window.location.search}`
		return false
	}

	if (auth && roles && !authStore.isRoleGranted(roles)) {
		window.location.href = `/login${window.location.search}`
		return false
	}

	if (checkAuth && authStore.isLogged) {
		return roles && !authStore.isRoleGranted(roles) ? route.path : authRedirect || "/"
	}
}

export function scopeToRole(scope: string | string[]): UserRole {
	const role = _castArray(scope)[0]?.toLowerCase()
	return role === "admin" ? UserRole.Admin : role === "analyst" ? UserRole.Analyst : UserRole.Unknown
}
