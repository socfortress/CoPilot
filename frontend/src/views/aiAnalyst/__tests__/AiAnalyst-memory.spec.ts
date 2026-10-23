/**
 * The AI Analyst page's Memory tab: only with the "Talon v2" setting on (decision 3), like Chat v2,
 * Usage and Budgets; its content is mounted when the tab is first opened, so nothing is asked for
 * before then. Every SOC role sees it (the backend checks each customer).
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { resetTalonApprovals } from "@/composables/useTalonApprovals"
import { resetTalonV2Availability } from "@/composables/useTalonV2Availability"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import AiAnalyst from "../AiAnalyst.vue"

const getAvailability = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonV2: { getAvailability: (signal?: AbortSignal) => getAvailability(signal) },
		talonActions: { list: () => Promise.resolve({ data: { success: true, message: "", actions: [] } }) }
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
	emits: ["update:value"],
	setup:
		(_, { slots, emit }) =>
		() =>
			h("div", [
				h("button", { "data-open": "memory", onClick: () => emit("update:value", "memory") }),
				slots.default?.()
			])
})
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

function render() {
	return mount(AiAnalyst, {
		global: {
			stubs: {
				Tabs,
				TabPane,
				TalonV2Chat: stub("TalonChatV2").default,
				TalonApprovalsList: stub("TalonApprovalsList").default,
				TalonUsagePanel: stub("TalonUsagePanel").default,
				TalonBudgets: stub("TalonBudgets").default,
				TalonMemory: stub("TalonMemory").default
			}
		}
	})
}

function signInAs(role: AuthUserRole) {
	useAuthStore().user = { access_token: "t", username: "u", email: "", role }
}

async function settle() {
	await flushPromises()
	await vi.dynamicImportSettled()
	await flushPromises()
}

enableAutoUnmount(afterEach)

describe("aI Analyst Memory tab", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetTalonV2Availability()
		resetTalonApprovals()
		getAvailability.mockReset()
	})

	it("off: no Memory tab", async () => {
		signInAs(AuthUserRole.Admin)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false } })
		const wrapper = render()
		await settle()
		expect(wrapper.find('[data-pane="memory"]').exists()).toBe(false)
	})

	it("availability unknown (a failed answer): no Memory tab", async () => {
		signInAs(AuthUserRole.Analyst)
		getAvailability.mockRejectedValue(new Error("down"))
		const wrapper = render()
		await settle()
		expect(wrapper.find('[data-pane="memory"]').exists()).toBe(false)
	})

	it.each([AuthUserRole.Admin, AuthUserRole.Analyst, AuthUserRole.Responder])(
		"on: the tab for role %s, its content mounted when first opened",
		async role => {
			signInAs(role)
			getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
			const wrapper = render()
			await settle()
			expect(wrapper.get('[data-pane="memory"]').text()).toContain("Memory")
			expect(wrapper.find('[data-testid="TalonMemory"]').exists()).toBe(false)
			await wrapper.get('[data-open="memory"]').trigger("click")
			await settle()
			expect(wrapper.find('[data-testid="TalonMemory"]').exists()).toBe(true)
		}
	)
})
