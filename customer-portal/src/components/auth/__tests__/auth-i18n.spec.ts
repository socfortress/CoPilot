import { mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import i18n from "@/lang"
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

/** The sign-in form speaks the user's language (#1310), and follows a change of it. */
describe("the sign-in form's language", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		query.value = { reason: "disabled" }
	})

	it("is English by default", () => {
		const wrapper = render()
		expect(wrapper.get("[data-testid=login-submit]").text()).toBe("Sign in")
		expect(wrapper.get("[data-testid=login-account-disabled]").text()).toBe(
			"Your session ended because your account was disabled."
		)
	})

	it("is Italian when the user picked Italian", () => {
		i18n.global.locale.value = "it"
		const wrapper = render()
		expect(wrapper.get("[data-testid=login-submit]").text()).toBe("Accedi")
		expect(wrapper.text()).toContain("Nome utente")
		expect(wrapper.get("[data-testid=login-username] input").attributes("placeholder")).toBe(
			"Inserisci il tuo nome utente"
		)
		expect(wrapper.get("[data-testid=login-account-disabled]").text()).toBe(
			"La tua sessione è terminata perché il tuo account è stato disattivato."
		)
	})

	it("changes language on screen, without a reload", async () => {
		const wrapper = render()
		i18n.global.locale.value = "de"
		await nextTick()
		expect(wrapper.get("[data-testid=login-submit]").text()).toBe("Anmelden")
	})
})
