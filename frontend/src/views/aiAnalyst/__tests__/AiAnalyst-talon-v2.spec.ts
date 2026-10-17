/**
 * The AI Analyst page's chat tab follows the "Talon v2" setting (`GET /talon/v2/availability`):
 * the v2 chat only when it is on, the v1 `TalonChat` otherwise (off, unknown, or the route
 * failing), and neither before the answer, so one never flashes before the other. The answer is
 * kept for the session and forgotten at logout.
 */
import { flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import {
	resetTalonV2Availability,
	TALON_V2_AVAILABILITY_TIMEOUT_MS,
	useTalonV2Availability
} from "@/composables/useTalonV2Availability"
import AiAnalyst from "../AiAnalyst.vue"

const getAvailability = vi.fn()

vi.mock("@/api", () => ({
	default: { talonV2: { getAvailability: (signal?: AbortSignal) => getAvailability(signal) } }
}))

function stub(name: string) {
	return { default: defineComponent({ name, setup: () => () => h("div", { "data-testid": name }) }) }
}
vi.mock("@/components/talonChat/TalonChatContainer.vue", () => stub("TalonChatV1"))
vi.mock("@/components/aiAnalyst/TalonOverview.vue", () => stub("TalonOverview"))
vi.mock("@/components/aiAnalyst/AlertsReportsList.vue", () => stub("AlertsReportsList"))
vi.mock("@/components/aiAnalyst/Feedback/FeedbackDashboard.vue", () => stub("FeedbackDashboard"))

// Every tab's content at once: the panes are lazy in the page.
const Passthrough = defineComponent({
	setup:
		(_, { slots }) =>
		() =>
			h("div", slots.default?.())
})

// The v2 chat is loaded on demand (`defineAsyncComponent`), so it is stubbed by name once it loads.
const TalonV2ChatStub = stub("TalonChatV2").default

function render() {
	return mount(AiAnalyst, {
		global: {
			stubs: { Tabs: Passthrough, TabPane: Passthrough, TalonV2Chat: TalonV2ChatStub }
		}
	})
}

describe("aI Analyst chat tab and the Talon v2 setting", () => {
	beforeEach(() => {
		resetTalonV2Availability()
		getAvailability.mockReset()
	})
	afterEach(() => {
		vi.useRealTimers()
	})

	it("off: the v1 chat, as today", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false } })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="TalonChatV1"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="TalonChatV2"]').exists()).toBe(false)
	})

	it("on: the v2 chat instead", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		const wrapper = render()
		await flushPromises()
		await vi.dynamicImportSettled()
		await flushPromises()
		expect(wrapper.find('[data-testid="TalonChatV2"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="TalonChatV1"]').exists()).toBe(false)
	})

	it("the availability route failing: the v1 chat", async () => {
		getAvailability.mockRejectedValue(new Error("404"))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="TalonChatV1"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="TalonChatV2"]').exists()).toBe(false)
	})

	it("neither chat before the answer", async () => {
		getAvailability.mockReturnValue(new Promise(() => {}))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="TalonChatV1"]').exists()).toBe(false)
		expect(wrapper.find('[data-testid="TalonChatV2"]').exists()).toBe(false)
	})

	it("an answer that never comes: the v1 chat after the timeout, and a late answer changes nothing", async () => {
		vi.useFakeTimers()
		let answer: (value: unknown) => void = () => {}
		let signal: AbortSignal | undefined
		getAvailability.mockImplementation((s?: AbortSignal) => {
			signal = s
			return new Promise(resolve => (answer = resolve))
		})
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="TalonChatV1"]').exists()).toBe(false)

		await vi.advanceTimersByTimeAsync(TALON_V2_AVAILABILITY_TIMEOUT_MS)
		await flushPromises()
		expect(wrapper.find('[data-testid="TalonChatV1"]').exists()).toBe(true)
		expect(signal?.aborted).toBe(true)

		answer({ data: { success: true, enabled: true } })
		await flushPromises()
		expect(wrapper.find('[data-testid="TalonChatV1"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="TalonChatV2"]').exists()).toBe(false)
	})

	it("the answer is asked once for the session, and again after logout", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		useTalonV2Availability()
		useTalonV2Availability()
		await flushPromises()
		const { available } = useTalonV2Availability()
		expect(available.value).toBe(true)
		expect(getAvailability).toHaveBeenCalledTimes(1)

		resetTalonV2Availability() // stores/auth.ts:setLogout
		expect(useTalonV2Availability().available.value).toBe(false)
		await flushPromises()
		expect(getAvailability).toHaveBeenCalledTimes(2)
	})
})
