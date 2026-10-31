import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useTalonChatAvailability } from "@/composables/common/useTalonChatAvailability"
import { useLocalesStore } from "@/stores/i18n"
import TalonAskAboutAlert from "../TalonAskAboutAlert.vue"
import { testRouter, thread, withProviders } from "./fixtures"

const talonChat = vi.hoisted(() => ({ getAvailability: vi.fn(), createThread: vi.fn(), listThreads: vi.fn() }))
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
	talonChat.listThreads.mockReset().mockResolvedValue({ data: { threads: [], next: null } })
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
		expect(talonChat.createThread).toHaveBeenCalledWith({ customer_code: "ACME", alert_id: 4127, language: "en" })
		expect(router.currentRoute.value.name).toBe("TalonChat")
		expect(router.currentRoute.value.query.thread).toBe("th-9")
	})

	it("goes to the open conversation about this alert instead of making another", async () => {
		talonChat.getAvailability.mockResolvedValue({ data: { customer_code: "ACME", enabled: true } })
		talonChat.listThreads.mockResolvedValue({
			data: {
				threads: [
					thread({ id: "other-alert", context_alert_id: 1 }),
					thread({ id: "gone", context_alert_id: 4127, accessible: false }),
					thread({ id: "other-customer", context_alert_id: 4127, customer_code: "BETA" }),
					thread({ id: "th-open", context_alert_id: 4127 })
				],
				next: null
			}
		})
		const { wrapper, router } = await render()
		await wrapper.get("[data-testid=talon-ask-about-alert-button]").trigger("click")
		await flushPromises()
		expect(talonChat.createThread).not.toHaveBeenCalled()
		expect(router.currentRoute.value.query.thread).toBe("th-open")
	})

	it("makes a new conversation when the only ones about the alert can't be used", async () => {
		talonChat.getAvailability.mockResolvedValue({ data: { customer_code: "ACME", enabled: true } })
		talonChat.listThreads.mockResolvedValue({
			data: { threads: [thread({ id: "gone", context_alert_id: 4127, accessible: false })], next: null }
		})
		talonChat.createThread.mockResolvedValue({ data: thread({ id: "th-new", context_alert_id: 4127 }) })
		useLocalesStore().apply("cs")
		const { wrapper, router } = await render()
		await wrapper.get("[data-testid=talon-ask-about-alert-button]").trigger("click")
		await flushPromises()
		expect(talonChat.createThread).toHaveBeenCalledWith({ customer_code: "ACME", alert_id: 4127, language: "cs" })
		expect(router.currentRoute.value.query.thread).toBe("th-new")
	})

	it("hides itself, and forgets the cached answer, when the switch was turned off", async () => {
		talonChat.getAvailability.mockResolvedValue({ data: { customer_code: "ACME", enabled: true } })
		talonChat.createThread.mockRejectedValue({ response: { status: 403, data: { code: "portal_off" } } })
		const { wrapper } = await render()
		await wrapper.get("[data-testid=talon-ask-about-alert-button]").trigger("click")
		await flushPromises()
		expect(wrapper.find("[data-testid=talon-ask-about-alert]").exists()).toBe(false)
		await useTalonChatAvailability().isEnabledFor("ACME")
		expect(talonChat.getAvailability).toHaveBeenCalledTimes(2)
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
