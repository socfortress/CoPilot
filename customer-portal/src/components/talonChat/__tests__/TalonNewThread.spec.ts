import type { PortalCustomer } from "@/types/auth"
import { flushPromises, mount } from "@vue/test-utils"
import { NSelect } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import i18n from "@/lang"
import { useLocalesStore } from "@/stores/i18n"
import TalonNewThread from "../TalonNewThread.vue"
import { thread } from "./fixtures"

const talonChat = vi.hoisted(() => ({ createThread: vi.fn(), getAvailability: vi.fn() }))
vi.mock("@/api", () => ({ default: { talonChat } }))

const ACME: PortalCustomer = { customer_code: "ACME", customer_name: "Acme Corp" }
const BETA: PortalCustomer = { customer_code: "BETA", customer_name: "Beta Ltd", read_only: true }

function render(customers: PortalCustomer[]) {
	return mount(TalonNewThread, { props: { customers } })
}

beforeEach(() => {
	setActivePinia(createPinia())
	talonChat.createThread.mockReset()
})

describe("a new Ask Talon conversation", () => {
	it("preselects the organization when the user has only one, and starts with it", async () => {
		talonChat.createThread.mockResolvedValue({ data: thread() })
		const wrapper = render([ACME])
		expect(wrapper.find("[data-testid=talon-new-thread-select]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=talon-new-thread-customer]").text()).toBe("Acme Corp")
		await wrapper.get("[data-testid=talon-new-thread]").trigger("submit")
		await flushPromises()
		expect(talonChat.createThread).toHaveBeenCalledWith({ customer_code: "ACME", language: "en" })
		expect(wrapper.emitted("created")).toEqual([[thread()]])
	})

	it("makes a user with several organizations choose one: nothing is picked for them", async () => {
		talonChat.createThread.mockResolvedValue({ data: thread({ customer_code: "BETA" }) })
		const wrapper = render([ACME, BETA])
		const select = wrapper.findComponent(NSelect)
		expect(select.props("value")).toBeNull()
		expect(select.props("options")).toEqual([
			{ label: "Acme Corp", value: "ACME" },
			{ label: "Beta Ltd", value: "BETA" }
		])
		expect(wrapper.get("[data-testid=talon-new-thread-start]").attributes("disabled")).toBeDefined()
		await wrapper.get("[data-testid=talon-new-thread]").trigger("submit")
		expect(talonChat.createThread).not.toHaveBeenCalled()

		// A read-only organization may be chosen: chatting is reading.
		select.vm.$emit("update:value", "BETA")
		await wrapper.get("[data-testid=talon-new-thread]").trigger("submit")
		await flushPromises()
		expect(talonChat.createThread).toHaveBeenCalledWith({ customer_code: "BETA", language: "en" })
	})

	it("asks for answers in the portal's language", async () => {
		talonChat.createThread.mockResolvedValue({ data: thread() })
		useLocalesStore().apply("de")
		const wrapper = render([ACME])
		await wrapper.get("[data-testid=talon-new-thread]").trigger("submit")
		await flushPromises()
		expect(talonChat.createThread).toHaveBeenCalledWith({ customer_code: "ACME", language: "de" })
	})

	it("says why a conversation can't start, by code", async () => {
		talonChat.createThread.mockRejectedValue({ response: { status: 409, data: { detail: "x", code: "thread_limit" } } })
		i18n.global.locale.value = "nl"
		const wrapper = render([ACME])
		await wrapper.get("[data-testid=talon-new-thread]").trigger("submit")
		await flushPromises()
		expect(wrapper.get("[data-testid=talon-new-thread-error]").text()).toBe(
			"Je hebt te veel open gesprekken. Sluit er eerst een."
		)
	})

	it("says when no organization has Ask Talon on", () => {
		const wrapper = render([])
		expect(wrapper.get("[data-testid=talon-new-thread-none]").text()).toBe("Ask Talon isn't on for any of your organizations.")
		expect(wrapper.find("[data-testid=talon-new-thread-start]").exists()).toBe(false)
	})
})
