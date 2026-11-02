/**
 * The customer's AI Automation section (talon-analyst D85, plan AP-2) is an admin's only, behind
 * the "Talon v2" setting (D54). Anyone else neither sees it nor asks for Talon v2's availability,
 * and a link to `?tab=AI Automation` reads no policy for them.
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
const getSectionStatus = vi.fn()
const tabQuery = ref<string | undefined>(undefined)

vi.mock("@/api", () => ({
	default: {
		talonV2: { getAvailability: (signal?: AbortSignal) => getAvailability(signal) },
		talonAutomation: { getPolicy: (...a: unknown[]) => getPolicy(...a) },
		customers: { getCustomerSectionStatus: (...a: unknown[]) => getSectionStatus(...a) }
	}
}))
vi.mock("@/composables/useNavigation", () => ({ useRouteQueryParam: () => computed(() => tabQuery.value) }))
// The AI Triggers section, opened to show the automation group's rail, reads nothing here.
vi.mock("@/components/customers/aiTriggers/CustomerAITriggers.vue", () => ({
	__esModule: true,
	default: defineComponent({ setup: () => () => h("div") })
}))

const props = {
	customer: { customer_code: "ACME", customer_name: "Acme" } as never,
	customerInfo: null,
	customerMeta: null,
	customerPortainerStackId: null
}

function render() {
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

const railItem = '[data-testid="rail-item-AI Automation"]'

enableAutoUnmount(afterEach)

describe("customer AI Automation section visibility", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetTalonV2Availability()
		tabQuery.value = "AI Triggers"
		getAvailability.mockReset().mockResolvedValue({ data: { success: true, enabled: true } })
		getPolicy.mockReset().mockReturnValue(new Promise(() => {}))
		getSectionStatus.mockReset().mockReturnValue(new Promise(() => {}))
	})

	it("an admin with Talon v2 on sees it", async () => {
		signInAs(AuthUserRole.Admin)
		const wrapper = render()
		await settle()
		expect(wrapper.find(railItem).exists()).toBe(true)
	})

	it("an admin with Talon v2 off doesn't", async () => {
		signInAs(AuthUserRole.Admin)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: false } })
		const wrapper = render()
		await settle()
		expect(wrapper.find('[data-testid="rail-item-AI Triggers"]').exists()).toBe(true)
		expect(wrapper.find(railItem).exists()).toBe(false)
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
			await settle()
			expect(wrapper.find('[data-testid="rail-item-AI Triggers"]').exists()).toBe(true)
			expect(wrapper.find(railItem).exists()).toBe(false)
			expect(getAvailability).not.toHaveBeenCalled()
		})
	}

	it("?tab=AI Automation: an admin with v2 on reads the policy", async () => {
		signInAs(AuthUserRole.Admin)
		tabQuery.value = "AI Automation"
		const wrapper = render()
		await settle()
		expect(getPolicy).toHaveBeenCalledWith("ACME", expect.any(AbortSignal))
		expect(wrapper.find('[data-section="AI Automation"]').isVisible()).toBe(true)
	})

	it("?tab=AI Automation: a non-admin makes no policy call and opens Info", async () => {
		signInAs(AuthUserRole.Analyst)
		tabQuery.value = "AI Automation"
		const wrapper = render()
		await settle()
		expect(getPolicy).not.toHaveBeenCalled()
		expect(getAvailability).not.toHaveBeenCalled()
		expect(wrapper.find('[data-section="AI Automation"]').exists()).toBe(false)
		expect(wrapper.find('[data-section="Info"]').exists()).toBe(true)
	})
})
