import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import ChangePassword from "../ChangePassword.vue"

const auth = vi.hoisted(() => ({ resetPassword: vi.fn() }))
const store = vi.hoisted(() => ({ userName: "acme.viewer", setPasswordChangeRequired: vi.fn() }))
const router = vi.hoisted(() => ({ replace: vi.fn() }))
const route = vi.hoisted(() => ({ query: { redirect: "/alerts/42" } as Record<string, string> }))

vi.mock("@/api", () => ({ default: { auth } }))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => store }))
vi.mock("vue-router", () => ({ useRouter: () => router, useRoute: () => route }))
vi.mock("@/app-layouts/common/Logo.vue", () => ({ default: defineComponent({ setup: () => () => h("span", "logo") }) }))

function render() {
	return mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(ChangePassword)) }))
}

async function fill(wrapper: ReturnType<typeof render>, current: string, next: string) {
	await wrapper.get("[data-testid=change-password-current] input").setValue(current)
	await wrapper.get("[data-testid=change-password-new] input").setValue(next)
	await wrapper.get("[data-testid=change-password-confirm] input").setValue(next)
	await wrapper.get("[data-testid=change-password-submit]").trigger("click")
	await flushPromises()
}

/** The page a user whose password an admin chose is held on (#1277). */
describe("choose a new password", () => {
	beforeEach(() => {
		auth.resetPassword.mockReset()
		auth.resetPassword.mockResolvedValue({ data: { success: true, message: "Password reset successfully" } })
		store.setPasswordChangeRequired.mockReset()
		router.replace.mockReset()
		route.query = { redirect: "/alerts/42" }
	})

	it("says why, for whom, and asks for the password received", () => {
		const wrapper = render()
		expect(wrapper.text()).toContain("Choose a new password")
		expect(wrapper.text()).toContain("set by your security team")
		expect(wrapper.text()).toContain("acme.viewer")
		expect(wrapper.text()).toContain("Password you received")
	})

	it("replaces the password, lets the user go and continues where they were going", async () => {
		const wrapper = render()
		await fill(wrapper, "Given-By-Admin-2026!", "My-Own-Choice-2026!")
		expect(auth.resetPassword).toHaveBeenCalledWith("acme.viewer", "My-Own-Choice-2026!", "Given-By-Admin-2026!")
		expect(store.setPasswordChangeRequired).toHaveBeenCalledWith(false)
		expect(router.replace).toHaveBeenCalledWith("/alerts/42")
	})

	it("refuses the password received as the new one, and sends nothing", async () => {
		const wrapper = render()
		await fill(wrapper, "Given-By-Admin-2026!", "Given-By-Admin-2026!")
		expect(auth.resetPassword).not.toHaveBeenCalled()
		expect(document.body.textContent).toContain("Choose a password different from the current one")
		expect(store.setPasswordChangeRequired).not.toHaveBeenCalled()
	})

	it("keeps the user here when the API refuses", async () => {
		auth.resetPassword.mockRejectedValue({ response: { data: { message: "Current password is incorrect" } } })
		const wrapper = render()
		await fill(wrapper, "Wrong-Guess-2026!", "My-Own-Choice-2026!")
		expect(document.body.textContent).toContain("Current password is incorrect")
		expect(store.setPasswordChangeRequired).not.toHaveBeenCalled()
		expect(router.replace).not.toHaveBeenCalled()
	})

	it("can only sign out otherwise", async () => {
		const wrapper = render()
		expect(wrapper.text()).not.toContain("Cancel")
		await wrapper.get("[data-testid=change-password-cancel]").trigger("click")
		expect(router.replace).toHaveBeenCalledWith({ name: "Logout" })
	})
})
