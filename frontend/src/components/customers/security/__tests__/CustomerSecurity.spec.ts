import { flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import CustomerSecurity from "../CustomerSecurity.vue"

const security = vi.hoisted(() => ({ listCustomerUsers: vi.fn(), getSmtpStatus: vi.fn() }))
vi.mock("@/api", () => ({ default: { security, auth: {} } }))

function user(id: number, username: string, mustChange: boolean) {
	return {
		id,
		username,
		email: `${username}@acme.example`,
		role_name: "customer_user",
		last_login_at: null,
		totp_enabled: false,
		must_change_password: mustChange
	}
}

function render() {
	return mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, () =>
					h(NDialogProvider, null, () => h(CustomerSecurity, { customerCode: "ACME" })))
		})
	)
}

/** The Security tab shows who still has to replace a password an admin chose (#1277). */
describe("customer security: password change pending", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		security.listCustomerUsers.mockResolvedValue({
			data: { success: true, users: [user(1, "held.user", true), user(2, "free.user", false)] }
		})
		security.getSmtpStatus.mockResolvedValue({ data: { success: true, configured: true } })
	})

	it("marks only the users still on a password an admin chose", async () => {
		const wrapper = render()
		await flushPromises()
		const [held, free] = wrapper.findAll("tbody tr")
		expect(held?.find("[data-testid=security-must-change-password]").text()).toBe("Password change pending")
		expect(free?.find("[data-testid=security-must-change-password]").exists()).toBe(false)
	})

	it("reads the list again on Refresh: the tab stays mounted while the user changes it", async () => {
		const wrapper = render()
		await flushPromises()
		security.listCustomerUsers.mockResolvedValue({
			data: { success: true, users: [user(1, "held.user", false), user(2, "free.user", false)] }
		})
		await wrapper.get("[data-testid=security-refresh]").trigger("click")
		await flushPromises()
		expect(security.listCustomerUsers).toHaveBeenCalledTimes(2)
		expect(wrapper.find("[data-testid=security-must-change-password]").exists()).toBe(false)
	})
})
