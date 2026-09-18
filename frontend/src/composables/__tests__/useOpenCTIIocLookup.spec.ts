/**
 * Inline OpenCTI badges (#1146): every IoC card on an alert asks for its own
 * value, and they must cost one request together, not one each.
 */

import type { Ref } from "vue"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { effectScope, ref } from "vue"
import { resetOpenCTIIocLookupCache, useOpenCTIIocLookup } from "../useOpenCTIIocLookup"

const lookupObservables = vi.fn()

vi.mock("@/api", () => ({
	default: { opencti: { lookupObservables: (...args: unknown[]) => lookupObservables(...args) } }
}))

function answer(found: Record<string, boolean>, truncated = false) {
	return {
		data: {
			truncated,
			results: Object.entries(found).map(([value, isFound]) => ({
				value,
				found: isFound,
				observables: isFound ? [{ id: `obs-${value}`, score: 60, labels: [], reports_count: 1 }] : []
			}))
		}
	}
}

function use(value: string, enabled: boolean | Ref<boolean> = true) {
	const state = effectScope().run(() => useOpenCTIIocLookup(value, enabled))
	if (!state) throw new Error("effect scope did not run")
	return state
}

async function settle() {
	await vi.advanceTimersByTimeAsync(60)
	await vi.runAllTimersAsync()
}

describe("useOpenCTIIocLookup", () => {
	beforeEach(() => {
		vi.useFakeTimers()
		resetOpenCTIIocLookupCache()
		lookupObservables.mockReset()
	})

	afterEach(() => {
		vi.useRealTimers()
	})

	it("batches every IoC on the page into one request", async () => {
		lookupObservables.mockResolvedValue(answer({ "1.2.3.4": true, "evil.com": false, abc: true }))

		const ip = use("1.2.3.4")
		const domain = use("evil.com")
		const hash = use("abc")
		expect(ip.loading.value).toBe(true)
		await settle()

		expect(lookupObservables).toHaveBeenCalledTimes(1)
		expect(lookupObservables).toHaveBeenCalledWith(["1.2.3.4", "evil.com", "abc"])
		expect(ip.result.value?.found).toBe(true)
		expect(domain.result.value?.found).toBe(false)
		expect(hash.result.value?.observables).toHaveLength(1)
		expect(ip.loading.value).toBe(false)
	})

	it("asks once for a value that appears twice, whatever its case", async () => {
		lookupObservables.mockResolvedValue(answer({ ABC: true }))

		const upper = use("ABC")
		const lower = use(" abc ")
		await settle()

		expect(lookupObservables).toHaveBeenCalledWith(["ABC"])
		expect(lower.result.value?.found).toBe(true)
		expect(upper.result.value?.found).toBe(true)
	})

	it("reuses a cached answer instead of asking again", async () => {
		lookupObservables.mockResolvedValue(answer({ "1.2.3.4": true }))
		use("1.2.3.4")
		await settle()

		const again = use("1.2.3.4")
		await settle()

		expect(lookupObservables).toHaveBeenCalledTimes(1)
		expect(again.result.value?.found).toBe(true)
	})

	it("splits more than 100 values across requests", async () => {
		lookupObservables.mockImplementation((values: string[]) =>
			Promise.resolve(answer(Object.fromEntries(values.map(v => [v, false]))))
		)
		for (let i = 0; i < 150; i++) use(`v${i}`)
		await settle()

		expect(lookupObservables).toHaveBeenCalledTimes(2)
		expect(lookupObservables.mock.calls.map(([values]) => values.length)).toEqual([100, 50])
	})

	it("does not cache a failure, and retry() asks again", async () => {
		lookupObservables.mockRejectedValueOnce(new Error("network"))
		lookupObservables.mockResolvedValueOnce(answer({ "1.2.3.4": true }))

		const state = use("1.2.3.4")
		await settle()
		expect(state.error.value).toBe(true)

		state.retry()
		await settle()
		expect(lookupObservables).toHaveBeenCalledTimes(2)
		expect(state.error.value).toBe(false)
		expect(state.result.value?.found).toBe(true)
	})

	it("does not reuse a 'not found' from a truncated answer", async () => {
		lookupObservables.mockResolvedValue(answer({ "1.2.3.4": false }, true))
		use("1.2.3.4")
		await settle()
		use("1.2.3.4")
		await settle()
		expect(lookupObservables).toHaveBeenCalledTimes(2)
	})

	it("never sends an oversized value that would fail the whole batch", async () => {
		lookupObservables.mockResolvedValue(answer({ ok: true }))
		const long = use(`http://x/${"a".repeat(2100)}`)
		use("ok")
		await settle()

		expect(lookupObservables).toHaveBeenCalledWith(["ok"])
		expect(long.result.value?.found).toBe(false)
	})

	it("stays quiet while disabled, then looks up once enabled", async () => {
		lookupObservables.mockResolvedValue(answer({ "1.2.3.4": true }))
		const enabled = ref(false)
		const state = use("1.2.3.4", enabled)
		await settle()
		expect(lookupObservables).not.toHaveBeenCalled()

		enabled.value = true
		await settle()
		expect(lookupObservables).toHaveBeenCalledTimes(1)
		expect(state.result.value?.found).toBe(true)
	})
})
