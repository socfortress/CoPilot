/**
 * The AI Analyst page's cost tabs (M5-9b): Usage only with the "Talon v2" setting on, Budgets only
 * with it on *and* for an admin (decision B; the backend refuses anyone else too). Each tab's
 * content is mounted when the tab is first opened, so nothing is asked for before then; with the
 * setting off the page has neither.
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

// Every pane at once, with its name; the buttons stand in for clicking a tab.
const Tabs = defineComponent({
	emits: ["update:value"],
	setup:
		(_, { slots, emit }) =>
		() =>
			h("div", [
				...["usage", "budgets"].map(name =>
					h("button", { "data-open": name, onClick: () => emit("update:value", name) }, name)
				),
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
				TalonBudgets: stub("TalonBudgets").default
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

describe("aI Analyst cost tabs", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetTalonV2Availability()
		resetTalonApprovals()
		getAvailability.mockReset()
	})

	it("off: no Usage and no Budgets, even for an admin", async () => {
		signInAs(AuthUserRole.Admin)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false, run_view: false } })
		const wrapper = render()
		await settle()
		expect(wrapper.find('[data-pane="usage"]').exists()).toBe(false)
		expect(wrapper.find('[data-pane="budgets"]').exists()).toBe(false)
		expect(wrapper.find('[data-testid="TalonChatV1"]').exists()).toBe(true)
	})

	it("on, an analyst: Usage, never Budgets", async () => {
		signInAs(AuthUserRole.Analyst)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true, run_view: true } })
		const wrapper = render()
		await settle()
		expect(wrapper.find('[data-pane="usage"]').exists()).toBe(true)
		expect(wrapper.find('[data-pane="budgets"]').exists()).toBe(false)
	})

	it("on, a responder: no Budgets either", async () => {
		signInAs(AuthUserRole.Responder)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		const wrapper = render()
		await settle()
		expect(wrapper.find('[data-pane="budgets"]').exists()).toBe(false)
	})

	it("on, an admin: Usage and Budgets, each mounted when first opened", async () => {
		signInAs(AuthUserRole.Admin)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		const wrapper = render()
		await settle()
		expect(wrapper.get('[data-pane="usage"]').text()).toContain("Usage")
		expect(wrapper.get('[data-pane="budgets"]').text()).toContain("Budgets")
		expect(wrapper.find('[data-testid="TalonUsagePanel"]').exists()).toBe(false)
		expect(wrapper.find('[data-testid="TalonBudgets"]').exists()).toBe(false)

		await wrapper.get('[data-open="usage"]').trigger("click")
		await settle()
		expect(wrapper.find('[data-testid="TalonUsagePanel"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="TalonBudgets"]').exists()).toBe(false)

		await wrapper.get('[data-open="budgets"]').trigger("click")
		await settle()
		expect(wrapper.find('[data-testid="TalonBudgets"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="TalonUsagePanel"]').exists()).toBe(true) // kept, as show:lazy does
	})
})
