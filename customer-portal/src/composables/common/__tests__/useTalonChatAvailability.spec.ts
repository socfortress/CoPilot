import { beforeEach, describe, expect, it, vi } from "vitest"
import { useTalonChatAvailability } from "../useTalonChatAvailability"

const getAvailability = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { talonChat: { getAvailability } } }))

function answer(enabled: boolean, extra: Record<string, unknown> = {}) {
	return Promise.resolve({
		data: { customer_code: null, enabled, log_search: false, can_draft: true, can_request_analysis: false, ...extra }
	})
}

describe("useTalonChatAvailability (talon-analyst D97)", () => {
	beforeEach(() => {
		getAvailability.mockReset()
		useTalonChatAvailability().reset()
	})

	it("is shown when the route says so, with what the user may do for that customer", async () => {
		getAvailability.mockImplementation(() => answer(true, { customer_code: "ACME" }))
		const { availabilityFor, isEnabledFor } = useTalonChatAvailability()
		expect(await isEnabledFor("ACME")).toBe(true)
		expect(await availabilityFor("ACME")).toEqual({
			customer_code: "ACME",
			enabled: true,
			log_search: false,
			can_draft: true,
			can_request_analysis: false
		})
		expect(getAvailability).toHaveBeenCalledTimes(1)
		expect(getAvailability).toHaveBeenCalledWith("ACME")
	})

	it("is hidden when the route says it is off", async () => {
		getAvailability.mockImplementation(() => answer(false))
		const { available, isEnabledFor, availabilityFor } = useTalonChatAvailability()
		expect(await isEnabledFor()).toBe(false)
		expect(await availabilityFor("ACME")).toBeNull()
		expect(available.value).toBe(false)
	})

	it("is hidden when the route fails, and asks again next time", async () => {
		getAvailability.mockImplementationOnce(() => Promise.reject(new Error("network")))
		getAvailability.mockImplementationOnce(() => answer(true))
		const { available, isEnabledFor } = useTalonChatAvailability()
		expect(await isEnabledFor()).toBe(false)
		expect(available.value).toBe(false)
		expect(await isEnabledFor()).toBe(true)
		expect(available.value).toBe(true)
		expect(getAvailability).toHaveBeenCalledTimes(2)
	})

	it("reads a malformed answer as off", async () => {
		getAvailability.mockImplementation(() => Promise.resolve({ data: { enabled: "true" } }))
		expect(await useTalonChatAvailability().isEnabledFor()).toBe(false)
	})

	it("exposes only the caller-wide answer to the menu, and forgets it on logout", async () => {
		getAvailability.mockImplementation(() => answer(true))
		const { available, isEnabledFor, reset } = useTalonChatAvailability()
		await isEnabledFor("ACME")
		expect(available.value).toBe(false)
		await isEnabledFor()
		expect(available.value).toBe(true)
		reset()
		expect(available.value).toBe(false)
		await isEnabledFor()
		expect(getAvailability).toHaveBeenCalledTimes(3)
	})

	it("tells a failed check apart from off: couldn't check is not cached", async () => {
		getAvailability.mockImplementationOnce(() => Promise.reject(new Error("network")))
		getAvailability.mockImplementationOnce(() => answer(false))
		const { lookup } = useTalonChatAvailability()
		expect((await lookup("ACME")).state).toBe("error")
		expect((await lookup("ACME")).state).toBe("off")
		expect((await lookup("ACME")).state).toBe("off")
		expect(getAvailability).toHaveBeenCalledTimes(2)
	})

	it("asks again for a customer whose switch a request found off", async () => {
		getAvailability.mockImplementation(() => answer(true))
		const { isEnabledFor, invalidate } = useTalonChatAvailability()
		await isEnabledFor("ACME")
		await isEnabledFor()
		invalidate("ACME")
		getAvailability.mockImplementation(() => answer(false))
		expect(await isEnabledFor("ACME")).toBe(false)
		expect(await isEnabledFor()).toBe(false)
		expect(getAvailability).toHaveBeenCalledTimes(4)
	})

	it("lets no lookup still in flight at logout set the next session's menu", async () => {
		let resolve: (value: unknown) => void = () => {}
		getAvailability.mockImplementationOnce(() => new Promise(r => (resolve = r)))
		const { available, isEnabledFor, reset } = useTalonChatAvailability()
		const pending = isEnabledFor()
		reset()
		resolve({ data: { enabled: true } })
		expect(await pending).toBe(false)
		expect(available.value).toBe(false)
	})
})
