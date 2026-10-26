/**
 * The AI Analyst page's Ops tab (talon-analyst D96): only with the "Talon v2" setting on, like Memory;
 * its content is mounted when the tab is first opened, so nothing is asked for before then. Every SOC
 * role sees it (the backend checks each finding's customer). An ops notification's link,
 * `?tab=ops&finding=<id>`, opens the tab on that finding; with v2 off it falls back to the Overview.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { routeLocationKey } from "vue-router"
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
	props: { value: { type: String, default: "" } },
	emits: ["update:value"],
	setup:
		(props, { slots, emit }) =>
		() =>
			h("div", { "data-active": props.value }, [
				h("button", { "data-open": "ops", onClick: () => emit("update:value", "ops") }),
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

const TalonOpsStub = defineComponent({
	props: { initialFinding: { type: Number, default: null } },
	setup: props => () => h("div", { "data-testid": "TalonOps", "data-finding": String(props.initialFinding) })
})

function render(query: Record<string, string> = {}) {
	return mount(AiAnalyst, {
		global: {
			provide: { [routeLocationKey as symbol]: { query } },
			stubs: {
				Tabs,
				TabPane,
				TalonV2Chat: stub("TalonChatV2").default,
				TalonApprovalsList: stub("TalonApprovalsList").default,
				TalonUsagePanel: stub("TalonUsagePanel").default,
				TalonBudgets: stub("TalonBudgets").default,
				TalonMemory: stub("TalonMemory").default,
				TalonOps: TalonOpsStub
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

describe("aI Analyst Ops tab", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetTalonV2Availability()
		resetTalonApprovals()
		getAvailability.mockReset()
	})

	it("off: no Ops tab", async () => {
		signInAs(AuthUserRole.Admin)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false } })
		const wrapper = render()
		await settle()
		expect(wrapper.find('[data-pane="ops"]').exists()).toBe(false)
	})

	it.each([AuthUserRole.Admin, AuthUserRole.Analyst, AuthUserRole.Responder])(
		"on: the tab for role %s, its content mounted when first opened",
		async role => {
			signInAs(role)
			getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
			const wrapper = render()
			await settle()
			expect(wrapper.get('[data-pane="ops"]').text()).toContain("Ops")
			expect(wrapper.find('[data-testid="TalonOps"]').exists()).toBe(false)
			await wrapper.get('[data-open="ops"]').trigger("click")
			await settle()
			expect(wrapper.find('[data-testid="TalonOps"]').exists()).toBe(true)
		}
	)

	it("a notification's link opens the tab on its finding", async () => {
		signInAs(AuthUserRole.Analyst)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		const wrapper = render({ tab: "ops", finding: "1207" })
		await settle()
		expect(wrapper.get('[data-testid="TalonOps"]').attributes("data-finding")).toBe("1207")
	})

	it("a link with a bad id opens the tab without a finding", async () => {
		signInAs(AuthUserRole.Analyst)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		const wrapper = render({ tab: "ops", finding: "../1" })
		await settle()
		expect(wrapper.get('[data-testid="TalonOps"]').attributes("data-finding")).toBe("null")
	})

	it("a link to the tab with v2 off shows the Overview", async () => {
		signInAs(AuthUserRole.Analyst)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false } })
		const wrapper = render({ tab: "ops", finding: "1" })
		await settle()
		expect(wrapper.find('[data-pane="ops"]').exists()).toBe(false)
		expect(wrapper.get("[data-active]").attributes("data-active")).toBe("overview")
	})
})
