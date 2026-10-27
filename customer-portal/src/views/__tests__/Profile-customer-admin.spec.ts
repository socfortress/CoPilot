import type { PortalCustomer } from "@/types/auth"
import { flushPromises, mount } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
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

/** The profile says what its user is: a customer admin of which customers, or a portal user (#1296). */
describe("profile: customer admin", () => {
	it("says a portal user is one, with no tag, no ring and no admin mark", async () => {
		store.accessibleCustomers = [customer("ACME", "Acme Rome", false)]
		const wrapper = mount(Profile)
		await flushPromises()
		expect(wrapper.find("[data-testid=profile-customer-admin]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=profile-role-description]").text()).toBe("Portal user")
		expect(wrapper.findAll("[data-testid=profile-customer]")).toHaveLength(1)
		expect(wrapper.find("[data-testid=profile-customer-admin-of]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=profile-avatar]").attributes("style") ?? "").not.toContain("--info-color")
	})

	it("tags a customer admin, says which customers' users they manage and marks those customers", async () => {
		store.accessibleCustomers = [
			customer("ACME", "Acme Rome", true),
			customer("BETA", "Beta Milan", false),
			customer("GAMMA", "Gamma Turin", true)
		]
		const wrapper = mount(Profile)
		await flushPromises()
		expect(wrapper.get("[data-testid=profile-customer-admin]").text()).toBe("Customer admin")
		expect(wrapper.get("[data-testid=profile-role-description]").text()).toBe(
			"Invites and manages the portal users of Acme Rome, Gamma Turin. Appointed by your SOC."
		)
		const chips = wrapper.findAll("[data-testid=profile-customer]")
		expect(chips.map(chip => chip.find("[data-testid=profile-customer-admin-of]").exists())).toEqual([true, false, true])
		expect(wrapper.get("[data-testid=profile-avatar]").attributes("style")).toContain("var(--info-color)")
	})

	it("tags a user who may only read every customer, and says so (#1312)", async () => {
		store.accessibleCustomers = [{ ...customer("ACME", "Acme Rome", false), read_only: true }]
		const wrapper = mount(Profile)
		await flushPromises()
		expect(wrapper.get("[data-testid=profile-read-only]").text()).toBe("Read-only")
		expect(wrapper.get("[data-testid=profile-role-description]").text()).toBe(
			"Can view your organization's data but not change it."
		)
		expect(wrapper.find("[data-testid=profile-customer-read-only]").text()).toBe("read-only")
	})

	it("names the customers a user may only read when they work on others (#1312)", async () => {
		store.accessibleCustomers = [
			{ ...customer("ACME", "Acme Rome", false), read_only: true },
			customer("BETA", "Beta Milan", false)
		]
		const wrapper = mount(Profile)
		await flushPromises()
		expect(wrapper.get("[data-testid=profile-role-description]").text()).toBe(
			"Can view the data of Acme Rome but not change it."
		)
		const chips = wrapper.findAll("[data-testid=profile-customer]")
		expect(chips.map(chip => chip.find("[data-testid=profile-customer-read-only]").exists())).toEqual([true, false])
	})
})
