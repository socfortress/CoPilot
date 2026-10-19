import type { RouteLocationNormalized } from "vue-router"
import * as jose from "jose"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useAuthStore } from "@/stores/auth"
import { RouteRole } from "@/types/auth"
import { authCheck, getSafeRedirect, PASSWORD_CHANGE_ROUTE } from "../auth"

vi.mock("@/api", () => ({ default: {} }))

function route(name: string, fullPath: string, meta: Record<string, unknown> = {}, query: Record<string, string> = {}) {
	return { name, fullPath, path: fullPath.split("?")[0], meta, query } as unknown as RouteLocationNormalized
}

const OVERVIEW = route("Overview", "/overview", { auth: true, roles: RouteRole.All })
const ALERT = route("AlertDetails", "/alerts/42?tab=ai", { auth: true, roles: RouteRole.All })
const CHANGE = route(PASSWORD_CHANGE_ROUTE, "/change-password", { auth: true, roles: RouteRole.All })

function signIn(mustChange: boolean) {
	const access = new jose.UnsecuredJWT({ scopes: ["customer_user"], customer_codes: ["ACME"] })
		.setSubject("acme.viewer")
		.setExpirationTime("2h")
		.encode()
	useAuthStore().setLogged({ access_token: access, token_type: "bearer", must_change_password: mustChange })
}

/** The router holds a user whose password an admin chose on the change (#1277). */
describe("authCheck: a password an admin chose", () => {
	beforeEach(() => setActivePinia(createPinia()))

	it("sends every page to the change, remembering where the user was going", () => {
		signIn(true)
		expect(authCheck(OVERVIEW)).toEqual({ name: PASSWORD_CHANGE_ROUTE, query: { redirect: "/overview" } })
		expect(authCheck(ALERT)).toEqual({ name: PASSWORD_CHANGE_ROUTE, query: { redirect: "/alerts/42?tab=ai" } })
	})

	it("lets the change itself open", () => {
		signIn(true)
		expect(authCheck(CHANGE)).toBeUndefined()
	})

	it("after the login, carries the login's own destination over", () => {
		signIn(true)
		const login = route("Login", "/login?redirect=/cases/7", { checkAuth: true }, { redirect: "/cases/7" })
		expect(authCheck(login)).toEqual({ name: PASSWORD_CHANGE_ROUTE, query: { redirect: "/cases/7" } })
	})

	it("leaves the change once the password is replaced, for where the user was going", () => {
		signIn(false)
		const change = route(PASSWORD_CHANGE_ROUTE, "/change-password?redirect=/alerts", CHANGE.meta, {
			redirect: "/alerts"
		})
		expect(authCheck(change)).toBe("/alerts")
		expect(authCheck(OVERVIEW)).toBeUndefined()
	})

	it("asks a signed-out visitor of the change to sign in first", () => {
		expect(authCheck(CHANGE)).toEqual({ path: "/login", query: { redirect: "/change-password" } })
	})

	it("never redirects back to the change after it", () => {
		expect(getSafeRedirect("/change-password")).toBe("/")
		expect(getSafeRedirect("/change-password?redirect=/x")).toBe("/")
		expect(getSafeRedirect("/change-passwords-guide")).toBe("/change-passwords-guide")
	})
})
