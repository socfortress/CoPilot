/** The status lights' one request (#1325): read per customer, a newer read wins, a failure is off. */
import { flushPromises } from "@vue/test-utils"
import { CanceledError } from "axios"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { effectScope, ref } from "vue"
import { useSectionStatus } from "../useSectionStatus"
import { statusFixture } from "./fixtures"

const getSectionStatus = vi.fn()

vi.mock("@/api", () => ({
	default: { customers: { getCustomerSectionStatus: (...a: unknown[]) => getSectionStatus(...a) } }
}))

function answer(code: string, overrides = {}) {
	return { data: { success: true, customer_code: code, sections: statusFixture(overrides) } }
}

function use(code: ReturnType<typeof ref<string>>) {
	const scope = effectScope()
	const result = scope.run(() => useSectionStatus(() => code.value ?? ""))
	if (!result) throw new Error("the scope ran nothing")
	return { ...result, stop: () => scope.stop() }
}

beforeEach(() => {
	getSectionStatus.mockReset()
})

describe("useSectionStatus", () => {
	it("reads the customer's status, and again for another customer", async () => {
		getSectionStatus.mockImplementation((code: string) =>
			Promise.resolve(answer(code, code === "GLOBEX" ? { portal_sla: { on: false } } : {}))
		)
		const code = ref("ACME")
		const { status, stop } = use(code)
		await flushPromises()
		expect(status.value?.portal_sla).toEqual({ on: true })
		code.value = "GLOBEX"
		await flushPromises()
		expect(getSectionStatus).toHaveBeenLastCalledWith("GLOBEX", expect.any(AbortSignal))
		expect(status.value?.portal_sla).toEqual({ on: false })
		stop()
	})

	it("aborts a read still in flight when a newer one starts, and takes only the newer answer", async () => {
		const signals: AbortSignal[] = []
		let resolveFirst: (value: unknown) => void = () => {}
		getSectionStatus
			.mockImplementationOnce((_code: string, signal: AbortSignal) => {
				signals.push(signal)
				return new Promise(resolve => {
					resolveFirst = resolve
				})
			})
			.mockImplementationOnce((code: string, signal: AbortSignal) => {
				signals.push(signal)
				return Promise.resolve(answer(code, { portal_sla: { on: false } }))
			})
		const { status, refresh, stop } = use(ref("ACME"))
		await refresh()
		expect(signals[0]?.aborted).toBe(true)
		resolveFirst(answer("ACME"))
		await flushPromises()
		expect(status.value?.portal_sla).toEqual({ on: false })
		stop()
	})

	it("ignores an answer for another customer, and leaves the lights off on a failure", async () => {
		getSectionStatus.mockResolvedValueOnce(answer("OTHER"))
		const { status, refresh, stop } = use(ref("ACME"))
		await flushPromises()
		expect(status.value).toBeNull()
		getSectionStatus.mockRejectedValueOnce(new Error("down"))
		await refresh()
		expect(status.value).toBeNull()
		getSectionStatus.mockRejectedValueOnce(new CanceledError())
		await refresh()
		expect(status.value).toBeNull()
		stop()
	})

	it("asks nothing without a customer, and aborts when its owner goes away", async () => {
		const empty = use(ref(""))
		await flushPromises()
		expect(getSectionStatus).not.toHaveBeenCalled()
		empty.stop()

		let signal: AbortSignal | undefined
		getSectionStatus.mockImplementation((_code: string, s: AbortSignal) => {
			signal = s
			return new Promise(() => {})
		})
		const { stop } = use(ref("ACME"))
		stop()
		expect(signal?.aborted).toBe(true)
	})
})
