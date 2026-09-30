import { describe, expect, it, vi } from "vitest"
import { effectScope } from "vue"
import { useLatestRequest } from "../useLatestRequest"

/** A request that stays pending until settled by hand, and rejects like axios on abort. */
function deferred(signal: AbortSignal) {
	let resolve!: () => void
	let reject!: (err: unknown) => void
	const promise = new Promise<void>((res, rej) => {
		resolve = res
		reject = rej
	})
	signal.addEventListener("abort", () => reject(Object.assign(new Error("canceled"), { __CANCEL__: true })))
	return { promise, resolve, reject }
}

describe("useLatestRequest", () => {
	it("is loading while the request runs, not after", async () => {
		const { loading, run } = useLatestRequest()
		let request!: ReturnType<typeof deferred>
		const done = run(signal => (request = deferred(signal)).promise)

		expect(loading.value).toBe(true)
		request.resolve()
		await done
		expect(loading.value).toBe(false)
	})

	it("aborts the load in flight when a new one starts, and only the latest clears loading", async () => {
		const { loading, run } = useLatestRequest()
		let second!: ReturnType<typeof deferred>
		const a = run(signal => deferred(signal).promise)
		const b = run(signal => (second = deferred(signal)).promise)

		await a
		expect(loading.value, "the superseded load must not clear it: its successor is running").toBe(true)

		second.resolve()
		await b
		expect(loading.value).toBe(false)
	})

	it("clears loading when the latest load is cancelled without a successor", async () => {
		// The bug: the lists cleared it only on success or on a non-cancel error.
		const { loading, run, cancel } = useLatestRequest()
		const done = run(signal => deferred(signal).promise)

		cancel()
		await done
		expect(loading.value).toBe(false)
	})

	it("reports the latest load's error, never a cancellation nor a superseded load's error", async () => {
		const onError = vi.fn()
		const { loading, run } = useLatestRequest()
		let first!: ReturnType<typeof deferred>
		let second!: ReturnType<typeof deferred>
		const a = run(signal => (first = deferred(signal)).promise, onError)
		const b = run(signal => (second = deferred(signal)).promise, onError)

		first.reject(new Error("late failure of a superseded load"))
		await a
		second.reject(new Error("boom"))
		await b

		expect(onError).toHaveBeenCalledTimes(1)
		expect((onError.mock.calls[0]![0] as Error).message).toBe("boom")
		expect(loading.value).toBe(false)
	})

	it("cancels the load in flight when its component goes away", async () => {
		const scope = effectScope()
		let signal!: AbortSignal
		const state = scope.run(() => useLatestRequest())!
		const done = state.run(s => {
			signal = s
			return deferred(s).promise
		})

		scope.stop()
		await done
		expect(signal.aborted).toBe(true)
		expect(state.loading.value).toBe(false)
	})
})
