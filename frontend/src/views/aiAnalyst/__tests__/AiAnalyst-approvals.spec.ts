/**
 * The AI Analyst page's Approvals tab (M5-11b, decision b) exists only with the "Talon v2" setting
 * on; its badge counts the proposals the user may decide now (`GET /api/talon/actions?scope=pending`),
 * read while the page is open, and nothing is read with the setting off or after the page is left.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { talonAction } from "@/components/talonChat/v2/__tests__/fixtures"
import { resetTalonApprovals, TALON_APPROVALS_POLL_MS } from "@/composables/useTalonApprovals"
import { resetTalonV2Availability } from "@/composables/useTalonV2Availability"
import AiAnalyst from "../AiAnalyst.vue"

const getAvailability = vi.fn()
const list = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonV2: { getAvailability: (signal?: AbortSignal) => getAvailability(signal) },
		talonActions: { list: (...a: unknown[]) => list(...a) }
	}
}))

function stub(name: string) {
	return { default: defineComponent({ name, setup: () => () => h("div", { "data-testid": name }) }) }
}
vi.mock("@/components/talonChat/TalonChatContainer.vue", () => stub("TalonChatV1"))
vi.mock("@/components/aiAnalyst/TalonOverview.vue", () => stub("TalonOverview"))
vi.mock("@/components/aiAnalyst/AlertsReportsList.vue", () => stub("AlertsReportsList"))
vi.mock("@/components/aiAnalyst/Feedback/FeedbackDashboard.vue", () => stub("FeedbackDashboard"))

const Tabs = defineComponent({
	setup:
		(_, { slots }) =>
		() =>
			h("div", slots.default?.())
})
// Every pane at once, with its tab label (the badge lives there).
const TabPane = defineComponent({
	props: { name: { type: String, default: "" }, tab: { type: String, default: "" } },
	setup:
		(props, { slots }) =>
		() =>
			h("section", { "data-pane": props.name }, [
				h("header", slots.tab ? slots.tab() : props.tab),
				slots.default?.()
			])
})
const Badge = defineComponent({
	props: { value: { type: Number, default: 0 } },
	setup: props => () => h("sup", { "data-testid": "talon-approvals-badge" }, String(props.value))
})

function render() {
	return mount(AiAnalyst, {
		global: {
			stubs: {
				Tabs,
				TabPane,
				Badge,
				NBadge: Badge,
				TalonV2Chat: stub("TalonChatV2").default,
				TalonApprovalsList: stub("TalonApprovalsList").default
			}
		}
	})
}

function answer(count: number, mine = 0) {
	const decide = Array.from({ length: count }, (_, i) => talonAction({ id: `d-${i}`, is_requester: false }))
	const own = Array.from({ length: mine }, (_, i) => talonAction({ id: `m-${i}`, can_decide: false }))
	return { data: { success: true, message: "", actions: [...decide, ...own] } }
}

enableAutoUnmount(afterEach)

describe("aI Analyst Approvals tab", () => {
	beforeEach(() => {
		resetTalonV2Availability()
		resetTalonApprovals()
		getAvailability.mockReset()
		list.mockReset()
	})
	afterEach(() => {
		vi.useRealTimers()
	})

	it("off: no Approvals tab, and nothing asked", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false } })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-pane="approvals"]').exists()).toBe(false)
		expect(wrapper.find('[data-testid="talon-approvals-tab"]').exists()).toBe(false)
		expect(list).not.toHaveBeenCalled()
		expect(wrapper.find('[data-testid="TalonChatV1"]').exists()).toBe(true)
	})

	it("the availability route failing: no Approvals tab either", async () => {
		getAvailability.mockRejectedValue(new Error("404"))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-pane="approvals"]').exists()).toBe(false)
		expect(list).not.toHaveBeenCalled()
	})

	it("on: the tab, the list, and a badge counting what the user may decide", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		list.mockResolvedValue(answer(2, 1))
		const wrapper = render()
		await flushPromises()
		await vi.dynamicImportSettled()
		await flushPromises()
		expect(list).toHaveBeenCalledWith("pending", expect.any(AbortSignal))
		const tab = wrapper.get('[data-testid="talon-approvals-tab"]')
		expect(tab.text()).toContain("Approvals")
		expect(tab.get('[data-testid="talon-approvals-badge"]').text()).toBe("2")
		expect(wrapper.find('[data-testid="TalonApprovalsList"]').exists()).toBe(true)
	})

	it("no badge when nothing waits for this user", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		list.mockResolvedValue(answer(0, 2))
		const wrapper = render()
		await flushPromises()
		expect(
			wrapper.get('[data-testid="talon-approvals-tab"]').find('[data-testid="talon-approvals-badge"]').exists()
		).toBe(false)
	})

	it("the badge follows the poll while the page is open, and the poll stops when it is left", async () => {
		vi.useFakeTimers()
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		list.mockResolvedValueOnce(answer(1)).mockResolvedValue(answer(3))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-approvals-badge"]').text()).toBe("1")
		await vi.advanceTimersByTimeAsync(TALON_APPROVALS_POLL_MS)
		expect(wrapper.get('[data-testid="talon-approvals-badge"]').text()).toBe("3")
		const calls = list.mock.calls.length
		wrapper.unmount()
		await vi.advanceTimersByTimeAsync(TALON_APPROVALS_POLL_MS * 3)
		expect(list.mock.calls.length).toBe(calls)
	})
})
