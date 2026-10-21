/**
 * The customer's AI Automation tab (talon-analyst D85, plan AP-2) is an admin's only, behind the
 * "Talon v2" setting (D54). Anyone else neither sees it nor asks for Talon v2's availability, and a
 * link to `?tab=AI Automation` reads no policy for them.
 */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { computed, defineComponent, h, ref } from "vue"
import { resetTalonV2Availability } from "@/composables/useTalonV2Availability"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import CustomerDetailsTabs from "../CustomerDetailsTabs.vue"

const getAvailability = vi.fn()
const getPolicy = vi.fn()
const tabQuery = ref<string | undefined>(undefined)

vi.mock("@/api", () => ({
	default: {
		talonV2: { getAvailability: (signal?: AbortSignal) => getAvailability(signal) },
		talonAutomation: { getPolicy: (...a: unknown[]) => getPolicy(...a) }
	}
}))
vi.mock("@/composables/useNavigation", () => ({ useRouteQueryParam: () => computed(() => tabQuery.value) }))

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

const props = {
	customer: { customer_code: "ACME", customer_name: "Acme" } as never,
	customerInfo: null,
	customerMeta: null,
	customerPortainerStackId: null
}

function render() {
	return mount(CustomerDetailsTabs, {
		props,
		global: { stubs: { NTabs: Tabs, Tabs, NTabPane: TabPane, TabPane, NScrollbar: Tabs } }
	})
}

/** With Naive's own tabs: only the selected pane mounts its content. */
function renderWithRealTabs() {
	return mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(CustomerDetailsTabs, props)) }))
}

function signInAs(role: AuthUserRole) {
	useAuthStore().user = { access_token: "t", username: "u", email: "", role }
}

async function settle() {
	await flushPromises()
	await vi.dynamicImportSettled()
	await flushPromises()
}

const pane = '[data-pane="AI Automation"]'

enableAutoUnmount(afterEach)

describe("customer AI Automation tab visibility", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetTalonV2Availability()
		tabQuery.value = undefined
		getAvailability.mockReset().mockResolvedValue({ data: { success: true, enabled: true } })
		getPolicy.mockReset().mockReturnValue(new Promise(() => {}))
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
		expect(wrapper.find('[data-pane="Info"]').exists()).toBe(true)
		expect(wrapper.find(pane).exists()).toBe(false)
	})

	for (const role of [
		AuthUserRole.Analyst,
		AuthUserRole.Responder,
		AuthUserRole.Scheduler,
		AuthUserRole.CustomerUser
	]) {
		it(`a ${AuthUserRole[role]} never sees it, nor asks for availability`, async () => {
			signInAs(role)
			const wrapper = render()
			await flushPromises()
			expect(wrapper.find('[data-pane="Info"]').exists()).toBe(true)
			expect(wrapper.find(pane).exists()).toBe(false)
			expect(getAvailability).not.toHaveBeenCalled()
		})
	}

	it("?tab=AI Automation: an admin with v2 on reads the policy", async () => {
		signInAs(AuthUserRole.Admin)
		tabQuery.value = "AI Automation"
		renderWithRealTabs()
		await settle()
		expect(getPolicy).toHaveBeenCalledWith("ACME", expect.any(AbortSignal))
	})

	it("?tab=AI Automation: a non-admin makes no policy call", async () => {
		signInAs(AuthUserRole.Analyst)
		tabQuery.value = "AI Automation"
		renderWithRealTabs()
		await settle()
		expect(getPolicy).not.toHaveBeenCalled()
		expect(getAvailability).not.toHaveBeenCalled()
	})
})
