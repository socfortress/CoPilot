/**
 * The customer's AI Automation tab (talon-analyst D85, plan AP-2) is an admin's only, and only with
 * the "Talon v2" setting on. Anyone else neither sees it nor asks for Talon v2's availability.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { computed, defineComponent, h } from "vue"
import { resetTalonV2Availability } from "@/composables/useTalonV2Availability"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import CustomerDetailsTabs from "../CustomerDetailsTabs.vue"

const getAvailability = vi.fn()

vi.mock("@/api", () => ({
	default: { talonV2: { getAvailability: (signal?: AbortSignal) => getAvailability(signal) } }
}))
vi.mock("@/composables/useNavigation", () => ({ useRouteQueryParam: () => computed(() => undefined) }))

// Every pane's name; only the outer "Customer" pane renders its content (the sub-tabs), so no
// tab's component is loaded.
const Tabs = defineComponent({
	setup:
		(_, { slots }) =>
		() =>
			h("div", slots.default?.())
})
const TabPane = defineComponent({
	props: { name: { type: String, default: "" } },
	setup:
		(props, { slots }) =>
		() =>
			h("section", { "data-pane": props.name }, props.name === "Customer" ? slots.default?.() : undefined)
})

function render() {
	return mount(CustomerDetailsTabs, {
		props: {
			customer: { customer_code: "ACME", customer_name: "Acme" } as never,
			customerInfo: null,
			customerMeta: null,
			customerPortainerStackId: null
		},
		global: { stubs: { NTabs: Tabs, Tabs, NTabPane: TabPane, TabPane, NScrollbar: Tabs } }
	})
}

function signInAs(role: AuthUserRole) {
	useAuthStore().user = { access_token: "t", username: "u", email: "", role }
}

const pane = '[data-pane="AI Automation"]'

enableAutoUnmount(afterEach)

describe("customer AI Automation tab visibility", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetTalonV2Availability()
		getAvailability.mockReset().mockResolvedValue({ data: { success: true, enabled: true } })
	})

	it("an admin with Talon v2 on sees it", async () => {
		signInAs(AuthUserRole.Admin)
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find(pane).exists()).toBe(true)
	})

	it("an admin with Talon v2 off doesn't", async () => {
		signInAs(AuthUserRole.Admin)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false } })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find(pane).exists()).toBe(false)
	})

	for (const role of [
		AuthUserRole.Analyst,
		AuthUserRole.Responder,
		AuthUserRole.Scheduler,
		AuthUserRole.CustomerUser
	]) {
		it(`a ${AuthUserRole[role] ?? role} never sees it, nor asks for availability`, async () => {
			signInAs(role)
			const wrapper = render()
			await flushPromises()
			expect(wrapper.find('[data-pane="Info"]').exists()).toBe(true)
			expect(wrapper.find(pane).exists()).toBe(false)
			expect(getAvailability).not.toHaveBeenCalled()
		})
	}
})
