import * as jose from "jose"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useAuthStore } from "../auth"

const me = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { portal: { me } } }))

function token(customerCodes: string[]) {
	return new jose.UnsecuredJWT({ scopes: ["customer_user"], customer_codes: customerCodes })
		.setSubject("acme.viewer")
		.encode()
}

function profile(customers: { customer_code: string; customer_name: string; is_customer_admin?: boolean }[]) {
	return Promise.resolve({ data: { success: true, username: "acme.viewer", role: "customer_user", customers } })
}

function signIn(codes = ["ACME", "BETA"]) {
	const store = useAuthStore()
	store.setLogged({ access_token: token(codes), token_type: "bearer" })
	return store
}

/**
 * The token carries only customer codes; `GET /customer_portal/me` names them and is
 * read live (#1243). The store must show something sensible before, during and after.
 */
describe("auth store: the user's customers", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		me.mockReset()
	})

	it("uses the token's codes until the profile answers", () => {
		const store = signIn()
		expect(store.accessibleCustomerCodes).toEqual(["ACME", "BETA"])
		expect(store.customerName("ACME")).toBe("ACME")
	})

	it("names the customers once the profile has loaded, and takes its list as the truth", async () => {
		me.mockImplementation(() => profile([{ customer_code: "ACME", customer_name: "Acme Rome" }]))
		const store = signIn()

		await store.loadProfile()

		expect(store.accessibleCustomers).toEqual([{ customer_code: "ACME", customer_name: "Acme Rome" }])
		// BETA was unassigned after login: the live list wins over the token.
		expect(store.accessibleCustomerCodes).toEqual(["ACME"])
		expect(store.customerName("ACME")).toBe("Acme Rome")
	})

	it("falls back to the code for a customer it cannot name", async () => {
		me.mockImplementation(() => profile([{ customer_code: "ACME", customer_name: "Acme Rome" }]))
		const store = signIn()
		await store.loadProfile()

		expect(store.customerName("ELSEWHERE")).toBe("ELSEWHERE")
		expect(store.customerName(null)).toBe("")
	})

	it("keeps the token's codes when the profile fails: names are never a reason to block", async () => {
		me.mockRejectedValue(new Error("down"))
		vi.spyOn(console, "error").mockImplementation(() => {})
		const store = signIn()

		await store.loadProfile()

		expect(store.accessibleCustomerCodes).toEqual(["ACME", "BETA"])
	})

	it("asks nothing before sign-in, and ignores an answer that arrives after sign-out", async () => {
		const store = useAuthStore()
		await store.loadProfile()
		expect(me).not.toHaveBeenCalled()

		let answer!: (value: unknown) => void
		me.mockImplementation(() => new Promise(resolve => (answer = resolve)))
		signIn()
		const loading = store.loadProfile()
		store.setLogout()
		answer({ data: { success: true, customers: [{ customer_code: "ACME", customer_name: "Acme Rome" }] } })
		await loading

		expect(store.customers).toBeNull()
	})

	it("forgets the previous session's customers on sign-in and on sign-out", async () => {
		me.mockImplementation(() => profile([{ customer_code: "ACME", customer_name: "Acme Rome" }]))
		const store = signIn()
		await store.loadProfile()

		store.setLogged({ access_token: token(["OTHER"]), token_type: "bearer" })
		expect(store.accessibleCustomerCodes).toEqual(["OTHER"])

		store.setLogout()
		expect(store.customers).toBeNull()
		expect(store.accessibleCustomerCodes).toEqual([])
	})
})

/** A customer admin manages their customers' portal users (#1296): the profile says so, live. */
describe("auth store: customer admins", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		me.mockReset()
	})

	it("is one only when the profile says so for some customer", async () => {
		const store = signIn()
		expect(store.isCustomerAdmin).toBe(false)
		me.mockImplementation(() =>
			profile([
				{ customer_code: "ACME", customer_name: "Acme", is_customer_admin: false },
				{ customer_code: "BETA", customer_name: "Beta", is_customer_admin: true }
			])
		)
		await store.loadProfile()
		expect(store.isCustomerAdmin).toBe(true)

		me.mockImplementation(() => profile([{ customer_code: "ACME", customer_name: "Acme" }]))
		await store.loadProfile()
		expect(store.isCustomerAdmin).toBe(false)
	})
})
