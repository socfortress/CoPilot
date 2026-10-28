import type { TenantUsers } from "@/types/users"
import { flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import UsersPage from "../UsersPage.vue"
import { tenantUser } from "./fixtures"

const users = vi.hoisted(() => ({
	list: vi.fn(),
	invite: vi.fn(),
	disable: vi.fn(),
	enable: vi.fn(),
	resetTotp: vi.fn(),
	issueTemporaryPassword: vi.fn(),
	setReadOnly: vi.fn()
}))
vi.mock("@/api", () => ({ default: { users } }))

const ACME = { customer_code: "ACME", customer_name: "Acme", is_customer_admin: true }

function listing(extra: Partial<TenantUsers> = {}): TenantUsers {
	return {
		customers: [ACME],
		smtp_configured: false,
		users: [
			tenantUser(1, "boss", {
				is_self: true,
				is_customer_admin: true,
				can_manage: false,
				managed_by_soc_reason: "This is your own account."
			}),
			tenantUser(2, "jane", { totp_enabled: true }),
			tenantUser(3, "shared", {
				can_manage: false,
				managed_by_soc_reason: "This account also belongs to another customer."
			})
		],
		...extra
	}
}

function render() {
	// The page under test, inside the providers it needs.
	const content = () => h(NDialogProvider, null, () => h(UsersPage))
	return mount(defineComponent({ setup: () => () => h(NMessageProvider, null, content) }), {
		attachTo: document.body
	})
}

function row(wrapper: ReturnType<typeof render>, username: string) {
	return wrapper.get(`[data-testid=users-row][data-user=${username}]`)
}

async function confirm(label: string) {
	await flushPromises()
	const button = [...document.querySelectorAll<HTMLButtonElement>(".n-dialog button")].find(b =>
		b.textContent?.includes(label)
	)
	button?.click()
	await flushPromises()
}

beforeEach(() => {
	setActivePinia(createPinia())
	for (const fn of Object.values(users)) fn.mockReset()
	users.list.mockResolvedValue({ data: listing() })
})

afterEach(() => {
	document.body.innerHTML = ""
})

/** A customer admin's Users page (#1296). */
describe("the users", () => {
	it("lists them, the caller first, with what to know about each", async () => {
		const wrapper = render()
		await flushPromises()
		expect(wrapper.findAll("[data-testid=users-row]").map(r => r.attributes("data-user"))).toEqual([
			"boss",
			"jane",
			"shared"
		])
		expect(row(wrapper, "boss").text()).toContain("You")
		expect(row(wrapper, "boss").find("[data-testid=users-tag-admin]").exists()).toBe(true)
		expect(row(wrapper, "jane").text()).toContain("2FA on")
		wrapper.unmount()
	})

	it("says why someone is not theirs to manage instead of offering what would be refused", async () => {
		const wrapper = render()
		await flushPromises()
		expect(row(wrapper, "shared").find("[data-testid=users-actions]").exists()).toBe(false)
		expect(row(wrapper, "shared").get("[data-testid=users-managed-elsewhere]").text()).toContain("another customer")
		expect(row(wrapper, "jane").find("[data-testid=users-actions]").exists()).toBe(true)
		wrapper.unmount()
	})

	it("tells a portal user who administers nothing that the page is not theirs", async () => {
		users.list.mockRejectedValue({
			response: { status: 403, data: { detail: "Only a customer administrator can manage users." } }
		})
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=users-forbidden]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=users-invite]").exists()).toBe(false)
		wrapper.unmount()
	})

	it("shows a failure with a retry that loads again", async () => {
		users.list.mockRejectedValueOnce({ response: { status: 500, data: { detail: "Failed to load the users" } } })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=panel-error]").text()).toContain("Failed to load the users")
		await wrapper.get("[data-testid=panel-error] button").trigger("click")
		await flushPromises()
		expect(wrapper.findAll("[data-testid=users-row]")).toHaveLength(3)
		wrapper.unmount()
	})
})

describe("what a customer admin does", () => {
	it("disables only once confirmed, enables straight away, and shows the answer", async () => {
		users.disable.mockResolvedValue({
			data: { user: tenantUser(2, "jane", { disabled: true }), message: "jane was disabled." }
		})
		users.enable.mockResolvedValue({ data: { user: tenantUser(2, "jane"), message: "jane was enabled." } })
		const wrapper = render()
		await flushPromises()
		await row(wrapper, "jane").get("[data-testid=users-toggle-disabled]").trigger("click")
		expect(users.disable).not.toHaveBeenCalled()
		await confirm("Disable")
		expect(users.disable).toHaveBeenCalledWith(2)
		expect(row(wrapper, "jane").find("[data-testid=users-tag-disabled]").exists()).toBe(true)
		// A disabled user gets no temporary password: they can't sign in to use it.
		expect(row(wrapper, "jane").get("[data-testid=users-temporary-password]").attributes("disabled")).toBeDefined()

		await row(wrapper, "jane").get("[data-testid=users-toggle-disabled]").trigger("click")
		await flushPromises()
		expect(users.enable).toHaveBeenCalledWith(2)
		expect(row(wrapper, "jane").find("[data-testid=users-tag-disabled]").exists()).toBe(false)
		wrapper.unmount()
	})

	it("makes a user read-only and lets them change data again, without a confirmation (#1312)", async () => {
		users.setReadOnly
			.mockResolvedValueOnce({ data: { user: tenantUser(2, "jane", { read_only: true }), message: "jane can now only read your data." } })
			.mockResolvedValueOnce({ data: { user: tenantUser(2, "jane"), message: "jane can change your data again." } })
		const wrapper = render()
		await flushPromises()
		const toggle = () => row(wrapper, "jane").get("[data-testid=users-toggle-read-only]")
		expect(toggle().text()).toBe("Make read-only")
		await toggle().trigger("click")
		await flushPromises()
		expect(users.setReadOnly).toHaveBeenLastCalledWith(2, true)
		expect(row(wrapper, "jane").find("[data-testid=users-tag-readOnly]").text()).toBe("Read-only")
		expect(toggle().text()).toBe("Allow changes")
		await toggle().trigger("click")
		await flushPromises()
		expect(users.setReadOnly).toHaveBeenLastCalledWith(2, false)
		expect(row(wrapper, "jane").find("[data-testid=users-tag-readOnly]").exists()).toBe(false)
		// Nobody the SOC manages gets the action.
		expect(row(wrapper, "shared").find("[data-testid=users-toggle-read-only]").exists()).toBe(false)
		wrapper.unmount()
	})

	it("resets 2FA once confirmed, and only for someone who has it", async () => {
		users.resetTotp.mockResolvedValue({
			data: { user: tenantUser(2, "jane"), message: "Two-factor authentication was reset." }
		})
		users.list.mockResolvedValue({
			data: listing({ users: [tenantUser(2, "jane", { totp_enabled: true }), tenantUser(4, "noauth")] })
		})
		const wrapper = render()
		await flushPromises()
		expect(row(wrapper, "noauth").get("[data-testid=users-reset-totp]").attributes("disabled")).toBeDefined()
		await row(wrapper, "jane").get("[data-testid=users-reset-totp]").trigger("click")
		await confirm("Reset 2FA")
		expect(users.resetTotp).toHaveBeenCalledWith(2)
		expect(row(wrapper, "jane").text()).toContain("2FA off")
		wrapper.unmount()
	})

	it("shows a temporary password once, and forgets it when closed", async () => {
		users.issueTemporaryPassword.mockResolvedValue({
			data: {
				user: tenantUser(2, "jane"),
				delivery: "shown",
				temporary_password: "Tmp-Pass-2026!",
				email_problem: "Email is not configured"
			}
		})
		const wrapper = render()
		await flushPromises()
		await row(wrapper, "jane").get("[data-testid=users-temporary-password]").trigger("click")
		await confirm("Issue")
		expect(users.issueTemporaryPassword).toHaveBeenCalledWith(2)
		expect(document.querySelector("[data-testid=temporary-password-value]")?.textContent?.trim()).toBe(
			"Tmp-Pass-2026!"
		)
		expect(document.querySelector("[data-testid=temporary-password-dialog]")?.textContent).toContain(
			"email is not configured"
		)
		;(document.querySelector("[data-testid=temporary-password-done]") as HTMLButtonElement).click()
		await flushPromises()
		await new Promise(resolve => setTimeout(resolve, 300))
		expect(document.body.textContent).not.toContain("Tmp-Pass-2026!")
		wrapper.unmount()
	})
})

describe("an invitation", () => {
	async function openInvite(wrapper: ReturnType<typeof render>) {
		await wrapper.get("[data-testid=users-invite]").trigger("click")
		await flushPromises()
		return {
			input: (testid: string) => document.querySelector<HTMLInputElement>(`[data-testid=${testid}] input`)!,
			submit: () => document.querySelector<HTMLButtonElement>("[data-testid=invite-submit]")!.click()
		}
	}

	function type(input: HTMLInputElement, value: string) {
		input.value = value
		input.dispatchEvent(new Event("input"))
	}

	it("says what is wrong before sending anything", async () => {
		const wrapper = render()
		await flushPromises()
		const dialog = await openInvite(wrapper)
		dialog.submit()
		await flushPromises()
		expect(users.invite).not.toHaveBeenCalled()
		expect(document.querySelector("[data-testid=invite-username-problem]")?.textContent).toContain(
			"Enter a username"
		)
		type(dialog.input("invite-username"), "jane doe")
		await flushPromises()
		expect(document.querySelector("[data-testid=invite-username-problem]")?.textContent).toContain("3 to 64")
		wrapper.unmount()
	})

	it("invites to the only customer administered, then shows the password once", async () => {
		users.invite.mockResolvedValue({
			data: {
				user: tenantUser(9, "newbie", { must_change_password: true }),
				delivery: "shown",
				temporary_password: "First-Pass-2026!",
				email_problem: "Email is not configured"
			}
		})
		const wrapper = render()
		await flushPromises()
		const dialog = await openInvite(wrapper)
		type(dialog.input("invite-username"), " newbie ")
		type(dialog.input("invite-email"), "newbie@acme.example")
		await flushPromises()
		dialog.submit()
		await flushPromises()
		expect(users.invite).toHaveBeenCalledWith({
			username: "newbie",
			email: "newbie@acme.example",
			customer_codes: ["ACME"],
			read_only: false
		})
		expect(row(wrapper, "newbie").find("[data-testid=users-tag-password]").exists()).toBe(true)
		expect(document.querySelector("[data-testid=temporary-password-value]")?.textContent?.trim()).toBe(
			"First-Pass-2026!"
		)
		wrapper.unmount()
	})

	it("invites a user who may only read, when the box is ticked (#1312)", async () => {
		users.invite.mockResolvedValue({
			data: { user: tenantUser(9, "auditor", { read_only: true }), delivery: "email", temporary_password: null, email_problem: null }
		})
		const wrapper = render()
		await flushPromises()
		const dialog = await openInvite(wrapper)
		type(dialog.input("invite-username"), "auditor")
		type(dialog.input("invite-email"), "auditor@acme.example")
		document.querySelector<HTMLElement>("[data-testid=invite-read-only]")!.click()
		await flushPromises()
		dialog.submit()
		await flushPromises()
		expect(users.invite).toHaveBeenCalledWith({
			username: "auditor",
			email: "auditor@acme.example",
			customer_codes: ["ACME"],
			read_only: true
		})
		expect(row(wrapper, "auditor").find("[data-testid=users-tag-readOnly]").exists()).toBe(true)
		wrapper.unmount()
	})

	it("says the password was emailed when it was, and shows none", async () => {
		users.list.mockResolvedValue({ data: listing({ smtp_configured: true }) })
		users.invite.mockResolvedValue({
			data: { user: tenantUser(9, "newbie"), delivery: "email", temporary_password: null, email_problem: null }
		})
		const wrapper = render()
		await flushPromises()
		const dialog = await openInvite(wrapper)
		type(dialog.input("invite-username"), "newbie")
		type(dialog.input("invite-email"), "newbie@acme.example")
		await flushPromises()
		dialog.submit()
		await flushPromises()
		expect(document.querySelector("[data-testid=temporary-password-emailed]")?.textContent).toContain(
			"newbie@acme.example"
		)
		expect(document.querySelector("[data-testid=temporary-password-value]")).toBeNull()
		wrapper.unmount()
	})

	it("keeps the dialog open with the API's refusal", async () => {
		users.invite.mockRejectedValue({ response: { status: 409, data: { detail: "That username is taken." } } })
		const wrapper = render()
		await flushPromises()
		const dialog = await openInvite(wrapper)
		type(dialog.input("invite-username"), "jane")
		type(dialog.input("invite-email"), "other@acme.example")
		await flushPromises()
		dialog.submit()
		await flushPromises()
		expect(document.querySelector("[data-testid=invite-error]")?.textContent).toContain("That username is taken.")
		wrapper.unmount()
	})
})
