/**
 * The AI Analyst page's Settings tab, which holds the global automation switch (talon-analyst D85,
 * plan AP-2): an admin's only, with the "Talon v2" setting on, and mounted when first opened.
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
				h("button", { "data-open": "settings", onClick: () => emit("update:value", "settings") }),
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
				TalonAutomationSettings: stub("TalonAutomationSettings").default
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

describe("aI Analyst settings tab", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetTalonV2Availability()
		resetTalonApprovals()
		getAvailability.mockReset().mockResolvedValue({ data: { success: true, enabled: true } })
	})

	it("an admin with v2 on: the tab, its switch mounted when first opened", async () => {
		signInAs(AuthUserRole.Admin)
		const wrapper = render()
		await settle()
		expect(wrapper.get('[data-pane="settings"]').text()).toContain("Settings")
		expect(wrapper.find('[data-testid="TalonAutomationSettings"]').exists()).toBe(false)
		await wrapper.get('[data-open="settings"]').trigger("click")
		await settle()
		expect(wrapper.find('[data-testid="TalonAutomationSettings"]').exists()).toBe(true)
	})

	it("an admin with v2 off: no tab", async () => {
		signInAs(AuthUserRole.Admin)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false } })
		const wrapper = render()
		await settle()
		expect(wrapper.find('[data-pane="settings"]').exists()).toBe(false)
	})

	for (const role of [AuthUserRole.Analyst, AuthUserRole.Responder]) {
		it(`a ${AuthUserRole[role]} with v2 on: no tab`, async () => {
			signInAs(role)
			const wrapper = render()
			await settle()
			expect(wrapper.find('[data-pane="usage"]').exists()).toBe(true)
			expect(wrapper.find('[data-pane="settings"]').exists()).toBe(false)
		})
	}
})
