import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import TalonAskAboutAlert from "../TalonAskAboutAlert.vue"
import { testRouter, thread, withProviders } from "./fixtures"

const talonChat = vi.hoisted(() => ({ getAvailability: vi.fn(), createThread: vi.fn() }))
vi.mock("@/api", () => ({ default: { talonChat } }))

async function render() {
	const router = testRouter()
	await router.push("/alerts/4127")
	const wrapper = mount(withProviders(TalonAskAboutAlert, { alertId: 4127, customerCode: "ACME" }), {
		global: { plugins: [router] }
	})
	await flushPromises()
	return { wrapper, router }
}

beforeEach(() => {
	setActivePinia(createPinia())
	useTalonChatAvailability().reset()
	talonChat.getAvailability.mockReset()
	talonChat.createThread.mockReset()
})

describe("ask Talon about this alert", () => {
	it("is hidden when Ask Talon is off for the alert's customer, or the check fails", async () => {
		talonChat.getAvailability.mockResolvedValue({ data: { enabled: false } })
		expect((await render()).wrapper.find("[data-testid=talon-ask-about-alert]").exists()).toBe(false)
		useTalonChatAvailability().reset()
		talonChat.getAvailability.mockRejectedValue(new Error("network"))
		expect((await render()).wrapper.find("[data-testid=talon-ask-about-alert]").exists()).toBe(false)
		expect(talonChat.getAvailability).toHaveBeenCalledWith("ACME")
	})

	it("opens a conversation with the alert as its context, and goes to it", async () => {
		talonChat.getAvailability.mockResolvedValue({ data: { customer_code: "ACME", enabled: true } })
		talonChat.createThread.mockResolvedValue({ data: thread({ id: "th-9", context_alert_id: 4127 }) })
		const { wrapper, router } = await render()
		await wrapper.get("[data-testid=talon-ask-about-alert-button]").trigger("click")
		await flushPromises()
		expect(talonChat.createThread).toHaveBeenCalledWith({ customer_code: "ACME", alert_id: 4127 })
		expect(router.currentRoute.value.name).toBe("TalonChat")
		expect(router.currentRoute.value.query.thread).toBe("th-9")
	})

	it("stays on the alert when the conversation can't be opened", async () => {
		talonChat.getAvailability.mockResolvedValue({ data: { customer_code: "ACME", enabled: true } })
		talonChat.createThread.mockRejectedValue({ response: { status: 404, data: { code: "alert_not_found" } } })
		const { wrapper, router } = await render()
		await wrapper.get("[data-testid=talon-ask-about-alert-button]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.path).toBe("/alerts/4127")
	})
})
