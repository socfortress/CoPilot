import * as jose from "jose"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useAuthStore } from "../auth"

const me = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { portal: { me } } }))

function token() {
	return new jose.UnsecuredJWT({ scopes: ["customer_user"], customer_codes: ["ACME"] })
		.setSubject("acme.viewer")
		.encode()
}

function profile(mustChange: boolean) {
	return Promise.resolve({
		data: {
			success: true,
			username: "acme.viewer",
			role: "customer_user",
			customers: [],
			must_change_password: mustChange
		}
	})
}

/** A password an admin chose holds the user on the change until they replace it (#1277). */
describe("auth store: a password an admin chose", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		me.mockReset()
	})

	it("takes the hold from the login", () => {
		const store = useAuthStore()
		store.setLogged({ access_token: token(), token_type: "bearer", must_change_password: true })
		expect(store.mustChangePassword).toBe(true)
	})

	it("starts without one when the login says nothing", () => {
		const store = useAuthStore()
		store.setLogged({ access_token: token(), token_type: "bearer" })
		expect(store.mustChangePassword).toBe(false)
	})

	it("follows the profile, read live: an admin may set a password after login", async () => {
		const store = useAuthStore()
		store.setLogged({ access_token: token(), token_type: "bearer" })
		me.mockImplementation(() => profile(true))
		await store.loadProfile()
		expect(store.mustChangePassword).toBe(true)

		me.mockImplementation(() => profile(false))
		await store.loadProfile()
		expect(store.mustChangePassword).toBe(false)
	})

	it("ends with the session", () => {
		const store = useAuthStore()
		store.setLogged({ access_token: token(), token_type: "bearer", must_change_password: true })
		store.setLogout()
		expect(store.mustChangePassword).toBe(false)
	})
})
