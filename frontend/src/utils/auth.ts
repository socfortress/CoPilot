import type { RouteLocationNormalized } from "vue-router"
import type { JWTRole, RouteMetaAuth } from "@/types/auth.d"
import { decodeJwt } from "jose"
import _castArray from "lodash/castArray"
import _toNumber from "lodash/toNumber"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth.d"

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

	// Logout handling
	if (route?.redirectedFrom?.name === "Logout") authStore.setLogout()

	// Auth check: if not logged or role not granted
	const loginPath = `/login${window.location.search}`

	if (auth && !authStore.isLogged) {
		window.location.replace(loginPath)
		return loginPath
	}

	if (auth && roles && !authStore.isRoleGranted(roles)) {
		window.location.replace(loginPath)
		return loginPath
	}

	if (checkAuth && authStore.isLogged) {
		return roles && !authStore.isRoleGranted(roles) ? route.path : authRedirect || "/"
	}
}

export function jwtRoleToUserRole(scope: JWTRole | JWTRole[]): AuthUserRole {
	const role = _castArray(scope)[0]?.toLowerCase() as JWTRole
	return role === "admin" ? AuthUserRole.Admin : role === "analyst" ? AuthUserRole.Analyst : AuthUserRole.Unknown
}
