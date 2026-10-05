import { beforeEach, describe, expect, it, vi } from "vitest"
import sla from "../sla"

const get = vi.hoisted(() => vi.fn())
vi.mock("../../httpClient", () => ({ HttpClient: { get } }))

describe("sLA endpoints (#1187)", () => {
	beforeEach(() => {
		get.mockReset()
	})

	it("asks availability for the caller, or for one customer, outliving a navigation", () => {
		sla.getAvailability()
		sla.getAvailability("ACME")
		const [[url, own], [, one]] = get.mock.calls
		expect(url).toBe("/customer_portal/sla/availability")
		expect(own.params).toBeUndefined()
		expect(one.params).toEqual({ customer_code: "ACME" })
		// The answer is cached as a shared promise: a navigation must not cancel it.
		expect(own.keepOnNavigation).toBe(true)
	})

	it("loads the overview for a period in UTC, scoped to the selected customers, cancellable", () => {
		const signal = new AbortController().signal
		sla.getOverview(new Date("2026-09-01T00:00:00Z"), new Date("2026-10-01T00:00:00Z"), ["A", "B"], signal)
		const [url, config] = get.mock.calls[0]!
		expect(url).toBe("/customer_portal/sla/overview")
		expect(config.params).toEqual({
			date_from: "2026-09-01T00:00:00.000Z",
			date_to: "2026-10-01T00:00:00.000Z",
			customer_codes: ["A", "B"]
		})
		expect(config.paramsSerializer).toEqual({ indexes: null })
		expect(config.signal).toBe(signal)
		expect(config.keepOnNavigation).toBeUndefined()
	})
})
