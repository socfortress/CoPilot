import type { RouteLocationNormalized } from "vue-router"
import type { RouteMetaAuth } from "@/types/auth"
import { decodeJwt } from "jose"
import _castArray from "lodash/castArray"
import _toNumber from "lodash/toNumber"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"

/**
 * Checks if the debounce time has elapsed since the last check
 * @param lastCheck - Date of the last check or null if never performed
 * @returns true if the debounce time has expired or if there was no previous check
 */
export function isDebounceTimeOver(lastCheck: Date | null) {
	const debounceTime = useAuthStore().tokenDebounceTime
	return !lastCheck || lastCheck.getTime() + _toNumber(debounceTime) * 1000 < Date.now()
}

/**
 * Checks if a JWT token is about to expire within a specified time threshold
 * @param token - JWT token to verify
 * @param threshold - Time threshold in seconds before expiration
 * @returns true if the token is expiring or already expired, false on decoding error
 */
export function isJwtExpiring(token: string, threshold: number): boolean {
	try {
		const { exp } = decodeJwt(token) || {}
		return exp ? Date.now() / 1000 > exp - threshold : true
	} catch {
		return false
	}
}

/**
 * Verifies user authentication and permissions for a given route
 * Handles logout, checks if the user is authenticated and has the required roles
 * @param route - Vue Router route to verify
 * @returns The redirect path if necessary, otherwise undefined
 */
export function authCheck(route: RouteLocationNormalized) {
	const { checkAuth, authRedirect, auth, roles }: RouteMetaAuth = route.meta
	const authStore = useAuthStore()

	// Logout handling
	if (route?.redirectedFrom?.name === "Logout") authStore.setLogout()

	if (authStore.isLogged && !authStore.userRole) authStore.setLogout()

	// Auth check: if not logged or role not granted
	const loginPath = `/login${window.location.search}`

	if (auth && !authStore.isLogged) {
		return loginPath
	}

	if (auth && roles && !authStore.isRoleGranted(roles)) {
		return loginPath
	}

	if (checkAuth && authStore.isLogged) {
		return roles && !authStore.isRoleGranted(roles) ? route.path : authRedirect || "/"
	}
}

/**
 * Converts a JWT role to an application user role
 * @param scope - Role name or array of role names from the JWT token
 * @returns The corresponding user role (Admin, Analyst or Unknown)
 */
export function jwtRoleToUserRole(scope: string | string[]): AuthUserRole | string | null {
	const role = _castArray(scope)[0]?.toLowerCase()

	switch (role) {
		case "admin":
			return AuthUserRole.Admin
		case "superuser":
			return AuthUserRole.Superuser
		case "analyst":
			return AuthUserRole.Analyst
		default:
			return role || null
	}
}
