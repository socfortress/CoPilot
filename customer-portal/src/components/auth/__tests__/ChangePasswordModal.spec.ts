import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import ChangePasswordModal from "../ChangePasswordModal.vue"

const auth = vi.hoisted(() => ({ resetPassword: vi.fn() }))

vi.mock("@/api", () => ({ default: { auth } }))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => ({ userName: "customer" }) }))
// The modal's teleport is not what these tests are about: render its content in place.
vi.mock("naive-ui", async original => {
	const { defineComponent, h } = await import("vue")
	return {
		...(await original<typeof import("naive-ui")>()),
		NModal: defineComponent({
			setup:
				(_props, { slots }) =>
				() =>
					h("div", [slots.default?.(), slots.footer?.()])
		})
	}
})

function render() {
	return mount(
		defineComponent({
			setup: () => () => h(NMessageProvider, null, () => h(ChangePasswordModal, { open: true }))
		})
	)
}

async function changePassword(newPassword: string) {
	const wrapper = render()
	const [current, next, confirm] = wrapper.findAll("input")
	await current.setValue("Old-Passw0rd")
	await next.setValue(newPassword)
	await confirm.setValue(newPassword)
	const submit = wrapper.findAll("button").find(button => button.text() === "Change Password")
	await submit?.trigger("click")
	await flushPromises()
	return wrapper
}

describe("changing my password in the portal (#1265)", () => {
	beforeEach(() => {
		auth.resetPassword.mockReset()
		auth.resetPassword.mockResolvedValue({ data: { success: true, message: "Password reset successfully" } })
	})

	afterEach(() => {
		document.body.innerHTML = ""
	})

	it.each(["Password1!-x", "Correct Horse 9+", "Pässwörd1_ok"])(
		"sends %s, which meets every rule",
		async password => {
			await changePassword(password)
			expect(auth.resetPassword).toHaveBeenCalledWith("customer", password, "Old-Passw0rd")
		}
	)

	it("names the rule a password breaks and sends nothing", async () => {
		await changePassword("password1-x")
		expect(auth.resetPassword).not.toHaveBeenCalled()
		expect(document.body.textContent).toContain("Password must contain an uppercase letter")
	})
})
