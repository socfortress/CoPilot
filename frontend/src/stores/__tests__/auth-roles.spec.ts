import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it } from "vitest"
import { AuthUserRole, RouteRole } from "@/types/auth"
import { jwtRoleToUserRole } from "@/utils/auth"
import { useAuthStore } from "../auth"

/** The responder role (#1219): an analyst who may also run response actions. */

function signedInAs(role: AuthUserRole) {
	const store = useAuthStore()
	store.user = { access_token: "t", username: "u", email: "", role }
	return store
}

beforeEach(() => setActivePinia(createPinia()))

describe("roles from the token", () => {
	it("reads the role from the first scope; a responder's token also says analyst", () => {
		expect(jwtRoleToUserRole(["responder", "analyst"])).toBe(AuthUserRole.Responder)
		expect(jwtRoleToUserRole(["analyst"])).toBe(AuthUserRole.Analyst)
		expect(jwtRoleToUserRole(["admin"])).toBe(AuthUserRole.Admin)
		expect(jwtRoleToUserRole(["scheduler" as never])).toBe(AuthUserRole.Unknown)
	})
})

describe("what each role may open and do", () => {
	it("lets a responder in wherever an analyst may go", () => {
		const store = signedInAs(AuthUserRole.Responder)
		expect(store.isRoleGranted([AuthUserRole.Admin, AuthUserRole.Analyst])).toBe(true)
		expect(store.isRoleGranted([AuthUserRole.Admin, AuthUserRole.Responder])).toBe(true)
		expect(store.isRoleGranted(RouteRole.All)).toBe(true)
		expect(store.isRoleGranted(AuthUserRole.Admin)).toBe(false)
	})

	it("keeps analysts out of the response pages", () => {
		const store = signedInAs(AuthUserRole.Analyst)
		expect(store.isRoleGranted([AuthUserRole.Admin, AuthUserRole.Responder])).toBe(false)
		expect(store.isRoleGranted([AuthUserRole.Admin, AuthUserRole.Analyst])).toBe(true)
	})

	it("lets admins and responders respond, not analysts", () => {
		expect(signedInAs(AuthUserRole.Admin).canRespond).toBe(true)
		expect(signedInAs(AuthUserRole.Responder).canRespond).toBe(true)
		expect(signedInAs(AuthUserRole.Analyst).canRespond).toBe(false)
		expect(signedInAs(AuthUserRole.Responder).isAdmin).toBe(false)
	})
})
