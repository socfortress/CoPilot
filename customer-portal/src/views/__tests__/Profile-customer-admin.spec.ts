import type { PortalCustomer } from "@/types/auth"
import { flushPromises, mount } from "@vue/test-utils"
import { afterEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import Profile from "../Profile.vue"

const store = vi.hoisted(() => ({
	userRoleName: "Customer_user",
	userName: "acme.lead",
	accessibleCustomers: [] as PortalCustomer[],
	userPic: ""
}))

vi.mock("vue-router", () => ({ useRoute: () => ({ query: {} }) }))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => store }))
vi.mock("@/composables/common/useServerNotifications", () => ({
	useServerNotifications: () => ({ available: ref(false), loadAvailability: vi.fn() })
}))

function stub(text: string) {
	return { default: defineComponent({ setup: () => () => h("div", { "data-testid": text }, text) }) }
}
vi.mock("@/components/profile/ProfileSettings.vue", () => stub("pane-settings"))
vi.mock("@/components/profile/NotificationPreferences.vue", () => stub("pane-notifications"))
vi.mock("@/components/auth/ChangePasswordCard.vue", () => stub("pane-password"))
vi.mock("@/components/auth/TotpToggle.vue", () => stub("pane-totp"))
vi.mock("@/components/common/CustomerName.vue", () => stub("customer-name"))

function customer(code: string, name: string, admin: boolean): PortalCustomer {
	return { customer_code: code, customer_name: name, is_customer_admin: admin }
}

/** The profile says when its user is a customer admin, and of which customers (#1296). */
describe("profile: customer admin", () => {
	afterEach(() => {
		document.body.innerHTML = ""
	})

	it("shows no tag for a portal user who administers nothing", async () => {
		store.accessibleCustomers = [customer("ACME", "Acme Rome", false)]
		const wrapper = mount(Profile)
		await flushPromises()
		expect(wrapper.find("[data-testid=profile-customer-admin]").exists()).toBe(false)
	})

	it("tags a customer admin beside their name, naming only the customers they administer", async () => {
		store.accessibleCustomers = [
			customer("ACME", "Acme Rome", true),
			customer("BETA", "Beta Milan", false),
			customer("GAMMA", "Gamma Turin", true)
		]
		const wrapper = mount(Profile, { attachTo: document.body })
		await flushPromises()
		const tag = wrapper.get("[data-testid=profile-customer-admin]")
		expect(tag.text()).toBe("Customer admin")
		await tag.trigger("mouseenter")
		await new Promise(resolve => setTimeout(resolve, 250))
		await flushPromises()
		expect(document.querySelector("[data-testid=profile-customer-admin-of]")?.textContent?.trim()).toBe(
			"Manages the portal users of Acme Rome, Gamma Turin"
		)
		wrapper.unmount()
	})
})
