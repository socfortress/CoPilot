import { beforeEach, describe, expect, it, vi } from "vitest"
import { useSocRequestsAvailability } from "../useSocRequestsAvailability"

const getAvailability = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { socRequests: { getAvailability } } }))

function answer(enabled: boolean) {
	return Promise.resolve({ data: { enabled, customer_code: null } })
}

describe("useSocRequestsAvailability (#1305)", () => {
	beforeEach(() => {
		getAvailability.mockReset()
		useSocRequestsAvailability().reset()
	})

	it("asks once per customer, sharing the request between callers", async () => {
		getAvailability.mockImplementation(() => answer(true))
		const { isEnabledFor } = useSocRequestsAvailability()
		const [first, second] = await Promise.all([isEnabledFor("ACME"), isEnabledFor("ACME")])
		await isEnabledFor("ACME")
		expect(first && second).toBe(true)
		expect(getAvailability).toHaveBeenCalledTimes(1)
	})

	it("exposes the caller-wide answer reactively, for the menu", async () => {
		getAvailability.mockImplementation(() => answer(true))
		const { available, isEnabledFor } = useSocRequestsAvailability()
		expect(available.value).toBe(false)
		await isEnabledFor("ACME")
		expect(available.value).toBe(false) // one customer's switch does not decide the menu
		await isEnabledFor()
		expect(available.value).toBe(true)
	})

	it("does not pin a failed lookup to off: the next caller retries", async () => {
		getAvailability.mockImplementationOnce(() => Promise.reject(new Error("network")))
		getAvailability.mockImplementationOnce(() => answer(true))
		const { isEnabledFor } = useSocRequestsAvailability()
		expect(await isEnabledFor()).toBe(false)
		expect(await isEnabledFor()).toBe(true)
		expect(getAvailability).toHaveBeenCalledTimes(2)
	})

	it("forgets everything on reset (logout): the next user may see other customers", async () => {
		getAvailability.mockImplementation(() => answer(true))
		const { available, isEnabledFor, reset } = useSocRequestsAvailability()
		await isEnabledFor()
		reset()
		expect(available.value).toBe(false)
		await isEnabledFor()
		expect(getAvailability).toHaveBeenCalledTimes(2)
	})
})
