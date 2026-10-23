/**
 * The AI Analyst page's Overview tab is the Talon health dashboard, whatever the "Talon v2" setting
 * says (decision b): it is told whether it is the tab shown (it refreshes only then) and whether the
 * page has a Usage tab, and its link to Usage switches the tab.
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
vi.mock("@/components/aiAnalyst/AlertsReportsList.vue", () => stub("AlertsReportsList"))
vi.mock("@/components/aiAnalyst/Feedback/FeedbackDashboard.vue", () => stub("FeedbackDashboard"))
vi.mock("@/components/aiAnalyst/TalonOverview.vue", () => ({
	default: defineComponent({
		name: "TalonOverview",
		props: { active: Boolean, usageAvailable: Boolean },
		emits: ["open-tab"],
		setup:
			(props, { emit }) =>
			() =>
				h(
					"button",
					{
						"data-testid": "overview",
						"data-active": String(props.active),
						"data-usage": String(props.usageAvailable),
						onClick: () => emit("open-tab", "usage")
					},
					"overview"
				)
	})
}))

// Every pane at once, with the active one marked.
const Tabs = defineComponent({
	props: { value: { type: String, default: "" } },
	setup:
		(props, { slots }) =>
		() =>
			h("div", { "data-active-tab": props.value }, slots.default?.())
})
const TabPane = defineComponent({
	props: { name: { type: String, default: "" }, tab: { type: String, default: "" } },
	setup:
		(props, { slots }) =>
		() =>
			h("section", { "data-pane": props.name }, [h("header", props.tab), slots.default?.()])
})

function render() {
	return mount(AiAnalyst, {
		global: {
			stubs: {
				Tabs,
				TabPane,
				TalonV2Chat: stub("TalonChatV2").default,
				TalonApprovalsList: stub("TalonApprovalsList").default,
				TalonUsagePanel: stub("TalonUsagePanel").default
			}
		}
	})
}

async function settle() {
	await flushPromises()
	await vi.dynamicImportSettled()
	await flushPromises()
}

enableAutoUnmount(afterEach)

describe("aI Analyst overview tab", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetTalonV2Availability()
		resetTalonApprovals()
		getAvailability.mockReset()
		useAuthStore().user = { access_token: "t", username: "u", email: "", role: AuthUserRole.Analyst }
	})

	it("is labelled Overview, shown first, and has no Usage tab with v2 off", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false, run_view: false } })
		const wrapper = render()
		await settle()
		expect(wrapper.get('[data-pane="overview"] header').text()).toBe("Overview")
		const overview = wrapper.get('[data-testid="overview"]')
		expect(overview.attributes("data-active")).toBe("true")
		expect(overview.attributes("data-usage")).toBe("false")
	})

	it("with v2 on, its Usage link opens the Usage tab", async () => {
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true, run_view: false } })
		const wrapper = render()
		await settle()
		expect(wrapper.get('[data-testid="overview"]').attributes("data-usage")).toBe("true")
		await wrapper.get('[data-testid="overview"]').trigger("click")
		await flushPromises()
		expect(wrapper.get("[data-active-tab]").attributes("data-active-tab")).toBe("usage")
		expect(wrapper.get('[data-testid="overview"]').attributes("data-active")).toBe("false")
	})
})
