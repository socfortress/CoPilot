import { beforeEach, describe, expect, it, vi } from "vitest"
import { useAuditAvailability } from "../useAuditAvailability"

const getAvailability = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { audit: { getAvailability } } }))

const ACME = { customer_code: "ACME", customer_name: "Acme" }

function answer(available: boolean) {
	return Promise.resolve({ data: { available, customers: available ? [ACME] : [] } })
}

describe("useAuditAvailability (#1298)", () => {
	beforeEach(() => {
		getAvailability.mockReset()
		useAuditAvailability().reset()
	})

	it("asks once, sharing the request between callers, and exposes the customers", async () => {
		getAvailability.mockImplementation(() => answer(true))
		const { available, customers, check } = useAuditAvailability()
		const [first, second] = await Promise.all([check(), check()])
		await check()
		expect(first && second).toBe(true)
		expect(getAvailability).toHaveBeenCalledTimes(1)
		expect(available.value).toBe(true)
		expect(customers.value).toEqual([ACME])
	})

	it("does not pin a failed lookup to off: the next caller retries", async () => {
		getAvailability.mockImplementationOnce(() => Promise.reject(new Error("network")))
		getAvailability.mockImplementationOnce(() => answer(true))
		const { check } = useAuditAvailability()
		expect(await check()).toBe(false)
		expect(await check()).toBe(true)
		expect(getAvailability).toHaveBeenCalledTimes(2)
	})

	it("forgets everything on reset (logout): the next user is someone else", async () => {
		getAvailability.mockImplementation(() => answer(true))
		const { available, customers, check, reset } = useAuditAvailability()
		await check()
		reset()
		expect(available.value).toBe(false)
		expect(customers.value).toEqual([])
		getAvailability.mockImplementation(() => answer(false))
		expect(await check()).toBe(false)
		expect(getAvailability).toHaveBeenCalledTimes(2)
	})
})
