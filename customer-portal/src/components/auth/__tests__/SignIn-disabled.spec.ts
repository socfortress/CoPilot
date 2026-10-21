import { mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import SignIn from "../SignIn.vue"

const query = vi.hoisted(() => ({ value: {} as Record<string, string> }))
vi.mock("vue-router", async original => ({
	...(await original<typeof import("vue-router")>()),
	useRoute: () => ({ query: query.value }),
	useRouter: () => ({ replace: vi.fn() })
}))
vi.mock("@/api", () => ({ default: {} }))

function render() {
	return mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(SignIn)) }))
}

/** Signed out because the account was disabled mid-session (#1296): the sign-in page says why. */
describe("sign-in after an account was disabled", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
	})

	it("says so when the sign-out carried that reason", () => {
		query.value = { reason: "disabled" }
		expect(render().get("[data-testid=login-account-disabled]").text()).toContain("Your account has been disabled")
	})

	it("says nothing otherwise", () => {
		query.value = {}
		expect(render().find("[data-testid=login-account-disabled]").exists()).toBe(false)
		query.value = { reason: "anything" }
		expect(render().find("[data-testid=login-account-disabled]").exists()).toBe(false)
	})
})
