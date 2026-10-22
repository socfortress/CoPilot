import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { AuthUserRole } from "@/types/auth"
import Profile from "../Profile.vue"

const store = vi.hoisted(() => ({ userRole: 0, userName: "", userEmail: "", userPic: "" }))
const auth = vi.hoisted(() => ({ getMyCustomerAccess: vi.fn() }))

vi.mock("@/stores/auth", () => ({ useAuthStore: () => store }))
vi.mock("@/api", () => ({ default: { auth } }))

function stub(text: string) {
	return { default: defineComponent({ setup: () => () => h("div", { "data-testid": text }, text) }) }
}
vi.mock("@/components/profile/ProfileSettings.vue", () => stub("pane-settings"))
vi.mock("@/components/profile/ProfileCustomers.vue", () => stub("pane-customers"))
vi.mock("@/components/auth/ChangePassword.vue", () => stub("pane-password"))
vi.mock("@/components/auth/TotpToggle.vue", () => stub("pane-totp"))
vi.mock("@/components/auth/PasskeyToggle.vue", () => stub("pane-passkey"))

async function render(role: AuthUserRole, access?: { customer_codes: string[]; scope?: string }) {
	store.userRole = role
	store.userName = "g.conti"
	auth.getMyCustomerAccess.mockResolvedValue({ data: { success: true, ...access } })
	const wrapper = mount(Profile)
	await flushPromises()
	return wrapper
}

/** The profile's header says the role, what it may do and which customers it reaches. */
describe("profile header: role", () => {
	beforeEach(() => {
		auth.getMyCustomerAccess.mockReset()
	})

	it("names a responder's role, says what it may do and counts the customers assigned", async () => {
		const wrapper = await render(AuthUserRole.Responder, { customer_codes: ["ACME", "BETA", "GAMMA"], scope: "assigned" })
		expect(wrapper.get("[data-testid=profile-role]").text()).toBe("Responder")
		expect(wrapper.get("[data-testid=profile-role-description]").text()).toMatch(/act on the endpoints/)
		expect(wrapper.get("[data-testid=profile-scope]").text()).toBe("3 customers assigned")
		expect(wrapper.get("[data-testid=profile-avatar]").attributes("style")).toContain("var(--primary-color)")
	})

	it("opens the Customers tab from the count", async () => {
		const wrapper = await render(AuthUserRole.Analyst, { customer_codes: ["ACME"], scope: "assigned" })
		expect(wrapper.get("[data-testid=profile-scope]").text()).toBe("1 customer assigned")
		await wrapper.get("[data-testid=profile-scope-link]").trigger("click")
		await flushPromises()
		expect(wrapper.find("[data-testid=pane-customers]").isVisible()).toBe(true)
	})

	it("says an admin sees every customer", async () => {
		const wrapper = await render(AuthUserRole.Admin, { customer_codes: ["*"], scope: "deployment" })
		expect(wrapper.get("[data-testid=profile-role]").text()).toBe("Admin")
		expect(wrapper.get("[data-testid=profile-scope]").text()).toBe("All customers")
	})

	it("asks nothing for a role without customers, and leaves the line out when the API fails", async () => {
		const scheduler = await render(AuthUserRole.Scheduler)
		expect(auth.getMyCustomerAccess).not.toHaveBeenCalled()
		expect(scheduler.find("[data-testid=profile-scope]").exists()).toBe(false)

		auth.getMyCustomerAccess.mockRejectedValue(new Error("down"))
		store.userRole = AuthUserRole.Analyst
		const failed = mount(Profile)
		await flushPromises()
		expect(failed.find("[data-testid=profile-scope]").exists()).toBe(false)
		expect(failed.get("[data-testid=profile-role]").text()).toBe("Analyst")
	})
})
