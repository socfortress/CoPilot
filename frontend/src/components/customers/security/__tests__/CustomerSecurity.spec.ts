import { flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import dayjs from "@/utils/dayjs"
import CustomerSecurity from "../CustomerSecurity.vue"

const security = vi.hoisted(() => ({
	listCustomerUsers: vi.fn(),
	getSmtpStatus: vi.fn(),
	setCustomerAdmin: vi.fn(),
	disableUser: vi.fn(),
	enableUser: vi.fn()
}))
vi.mock("@/api", () => ({ default: { security, auth: {} } }))

function user(id: number, username: string, mustChange: boolean, extra: Record<string, unknown> = {}) {
	return {
		id,
		username,
		email: `${username}@acme.example`,
		role_name: "customer_user",
		last_login_at: null,
		totp_enabled: false,
		must_change_password: mustChange,
		is_customer_admin: false,
		disabled_at: null,
		...extra
	}
}

/** Click the dialog's confirm button (naive renders dialogs in the body). */
async function confirm(label: string) {
	await flushPromises()
	const button = [...document.querySelectorAll<HTMLButtonElement>(".n-dialog button")].find(b =>
		b.textContent?.includes(label)
	)
	button?.click()
	await flushPromises()
}

function render() {
	// The component under test, inside the providers it needs.
	const content = () => h(NDialogProvider, null, () => h(CustomerSecurity, { customerCode: "ACME" }))

	return mount(
		defineComponent({
			setup: () => () => h(NMessageProvider, null, content)
		}),
		{ attachTo: document.body }
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

	it("reads the last sign-in as UTC, and says 2FA is On or Off (Disabled is the account's state)", async () => {
		const guess = vi.spyOn(dayjs.tz, "guess").mockReturnValue("Europe/Rome")
		security.listCustomerUsers.mockResolvedValue({
			data: {
				success: true,
				users: [
					user(1, "with.2fa", false, { totp_enabled: true, last_login_at: "2026-10-22T12:01:00" }),
					user(2, "without.2fa", false)
				]
			}
		})
		const wrapper = render()
		await flushPromises()
		const [on, off] = wrapper.findAll("tbody tr")
		// 12:01 UTC is 14:01 in Rome (CEST).
		expect(on?.get("[data-testid=security-last-login]").text()).toBe("10/22/2026 14:01")
		expect(on?.get("[data-testid=security-totp]").text()).toBe("On")
		expect(off?.get("[data-testid=security-last-login]").text()).toBe("Never")
		expect(off?.get("[data-testid=security-totp]").text()).toBe("Off")
		guess.mockRestore()
	})
})

/** Customer admins and disabled accounts (#1296): the SOC appoints the one and can do the other. */
describe("customer security: customer admins and disabled accounts", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		document.body.innerHTML = ""
		for (const fn of Object.values(security)) fn.mockReset()
		security.getSmtpStatus.mockResolvedValue({ data: { success: true, configured: true } })
		security.setCustomerAdmin.mockResolvedValue({ data: { success: true, message: "ok" } })
		security.disableUser.mockResolvedValue({ data: { success: true, message: "ok" } })
		security.enableUser.mockResolvedValue({ data: { success: true, message: "ok" } })
		security.listCustomerUsers.mockResolvedValue({
			data: {
				success: true,
				users: [
					user(1, "boss", false, { is_customer_admin: true }),
					user(2, "gone", false, { disabled_at: "2026-10-01T09:00:00" }),
					user(3, "ana", false, { role_name: "analyst" })
				]
			}
		})
	})

	it("tags who administers the customer's portal users and who is disabled", async () => {
		const wrapper = render()
		await flushPromises()
		const [boss, gone, ana] = wrapper.findAll("tbody tr")
		expect(boss?.find("[data-testid=security-customer-admin]").text()).toBe("Customer admin")
		expect(boss?.find("[data-testid=security-disabled]").exists()).toBe(false)
		expect(gone?.find("[data-testid=security-disabled]").text()).toBe("Disabled")
		// A SOC user is neither appointed nor disabled here.
		expect(ana?.find("[data-testid=security-toggle-customer-admin]").exists()).toBe(false)
		expect(ana?.find("[data-testid=security-toggle-disabled]").exists()).toBe(false)
		wrapper.unmount()
	})

	it("appoints and removes a customer admin once confirmed, then reads the list again", async () => {
		const wrapper = render()
		await flushPromises()
		const [boss, gone] = wrapper.findAll("tbody tr")
		expect(boss?.get("[data-testid=security-toggle-customer-admin]").text()).toBe("Remove customer admin")
		await gone?.get("[data-testid=security-toggle-customer-admin]").trigger("click")
		expect(security.setCustomerAdmin).not.toHaveBeenCalled()
		await confirm("Make customer admin")
		expect(security.setCustomerAdmin).toHaveBeenCalledWith("ACME", 2, true)
		expect(security.listCustomerUsers).toHaveBeenCalledTimes(2)

		await boss?.get("[data-testid=security-toggle-customer-admin]").trigger("click")
		await confirm("Remove")
		expect(security.setCustomerAdmin).toHaveBeenLastCalledWith("ACME", 1, false)
		wrapper.unmount()
	})

	it("disables only once confirmed, and enables straight away", async () => {
		const wrapper = render()
		await flushPromises()
		const [boss, gone] = wrapper.findAll("tbody tr")
		expect(gone?.get("[data-testid=security-toggle-disabled]").text()).toBe("Enable")
		await gone?.get("[data-testid=security-toggle-disabled]").trigger("click")
		await flushPromises()
		expect(security.enableUser).toHaveBeenCalledWith(2)

		await boss?.get("[data-testid=security-toggle-disabled]").trigger("click")
		expect(security.disableUser).not.toHaveBeenCalled()
		await confirm("Disable")
		expect(security.disableUser).toHaveBeenCalledWith(1)
		wrapper.unmount()
	})
})
