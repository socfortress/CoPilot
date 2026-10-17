/**
 * The v2 conversation header's thread total: the API's string, read again after a completed turn;
 * marked when incomplete; nothing at all when the read fails (the header as before).
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import TalonThreadCost from "../TalonThreadCost.vue"
import { figures, refused } from "./fixtures"

const getThreadUsage = vi.fn()

vi.mock("@/api", () => ({
	default: { talonUsage: { getThreadUsage: (...a: unknown[]) => getThreadUsage(...a) } }
}))

const THREAD = "0b6f0c55-7a39-4e57-9d6e-3f1a2b3c4d5e"

function answer(cost: string, complete = true) {
	return {
		data: {
			thread_id: THREAD,
			customer_code: "ACME",
			groups: [],
			truncated: false,
			total: figures(cost, { cost_complete: complete })
		}
	}
}

enableAutoUnmount(afterEach)

describe("talon thread cost", () => {
	beforeEach(() => {
		getThreadUsage.mockReset()
	})

	it("the total as the API's string, read again after a turn", async () => {
		getThreadUsage.mockResolvedValueOnce(answer("0.1")).mockResolvedValueOnce(answer("0.30", false))
		const wrapper = mount(TalonThreadCost, { props: { threadId: THREAD, refreshKey: 0 } })
		await flushPromises()
		expect(getThreadUsage).toHaveBeenCalledWith(THREAD, expect.any(AbortSignal))
		expect(wrapper.get('[data-testid="talon-v2-thread-cost"]').text()).toBe("0.1 USD")
		await wrapper.setProps({ refreshKey: 1 })
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-v2-thread-cost"]').text()).toBe("0.30 USD+")
	})

	it("a refusal shows nothing", async () => {
		getThreadUsage.mockRejectedValue(refused(404, "thread not found"))
		const wrapper = mount(TalonThreadCost, { props: { threadId: THREAD } })
		await flushPromises()
		expect(wrapper.find('[data-testid="talon-v2-thread-cost"]').exists()).toBe(false)
	})
})
