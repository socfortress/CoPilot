import type { CustomerPortalChatSettings } from "@/types/customer-portal"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import PortalChatSettings from "../PortalChatSettings.vue"

const getCustomerPortalChatSettings = vi.fn()
const setCustomerPortalChatSettings = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		customerPortal: {
			getCustomerPortalChatSettings: (...args: unknown[]) => getCustomerPortalChatSettings(...args),
			setCustomerPortalChatSettings: (...args: unknown[]) => setCustomerPortalChatSettings(...args)
		},
		talonPortalReview: { listThreads: vi.fn(), getMessages: vi.fn() }
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))

function answer(over: Partial<CustomerPortalChatSettings> = {}, aiReports = true) {
	return {
		data: {
			success: true,
			message: "",
			settings: {
				customer_code: "ACME",
				portal_chat_enabled: false,
				log_search_enabled: false,
				daily_message_limit: null,
				user_daily_message_limit: null,
				version: null,
				updated_at: null,
				updated_by: null,
				...over
			},
			ai_reports_enabled: aiReports,
			proposed: { daily_message_limit: 200, user_daily_message_limit: 50 }
		}
	}
}

async function render(aiReportsEnabled: boolean | null = true) {
	const Host = defineComponent({
		render: () => h(NMessageProvider, () => h(PortalChatSettings, { customerCode: "ACME", aiReportsEnabled }))
	})
	const wrapper = mount(Host)
	await flushPromises()
	return wrapper
}

function switchOf(wrapper: Awaited<ReturnType<typeof render>>, testId: string) {
	return wrapper.get(`[data-testid=${testId}]`)
}

function disabled(wrapper: Awaited<ReturnType<typeof render>>, testId: string) {
	return switchOf(wrapper, testId).classes().includes("n-switch--disabled")
}

beforeEach(() => {
	getCustomerPortalChatSettings.mockReset()
	setCustomerPortalChatSettings.mockReset()
	auth.isAdmin = true
})

describe("the portal chat settings", () => {
	it("turning the chat on proposes the limits, and saves every field", async () => {
		getCustomerPortalChatSettings.mockResolvedValue(answer())
		setCustomerPortalChatSettings.mockResolvedValue(
			answer({ portal_chat_enabled: true, daily_message_limit: 200, user_daily_message_limit: 50, version: 1 })
		)
		const wrapper = await render()
		expect(wrapper.get("[data-testid=portal-chat-state]").text()).toContain("can't chat with Talon")

		await switchOf(wrapper, "portal-chat-switch").trigger("click")
		await nextTick()
		expect((wrapper.get("[data-testid=portal-chat-daily-limit] input").element as HTMLInputElement).value).toBe(
			"200"
		)
		expect((wrapper.get("[data-testid=portal-chat-user-limit] input").element as HTMLInputElement).value).toBe("50")

		await wrapper.get("[data-testid=portal-chat-save]").trigger("click")
		await flushPromises()
		expect(setCustomerPortalChatSettings).toHaveBeenCalledWith("ACME", {
			portal_chat_enabled: true,
			log_search_enabled: false,
			daily_message_limit: 200,
			user_daily_message_limit: 50
		})
		expect(wrapper.get("[data-testid=portal-chat-state]").text()).toContain("can chat with Talon")
	})

	it("can't be turned on while the customer's AI reports are off", async () => {
		getCustomerPortalChatSettings.mockResolvedValue(answer({}, false))
		const wrapper = await render(false)
		expect(disabled(wrapper, "portal-chat-switch")).toBe(true)
		expect(wrapper.get("[data-testid=portal-chat-state]").text()).toContain("Turn on the AI findings above first")
	})

	it("shows why the limits can't be saved, and doesn't send them", async () => {
		getCustomerPortalChatSettings.mockResolvedValue(
			answer({ portal_chat_enabled: true, daily_message_limit: 200, user_daily_message_limit: 50, version: 2 })
		)
		const wrapper = await render()
		const perUser = wrapper.get("[data-testid=portal-chat-user-limit] input")
		await perUser.setValue("500")
		await perUser.trigger("blur")
		await flushPromises()
		expect(wrapper.get("[data-testid=portal-chat-problem]").text()).toContain("can't be more than the customer's")
		expect(wrapper.get("[data-testid=portal-chat-save]").attributes("disabled")).toBeDefined()
		expect(setCustomerPortalChatSettings).not.toHaveBeenCalled()
	})

	it("is read-only for an analyst", async () => {
		auth.isAdmin = false
		getCustomerPortalChatSettings.mockResolvedValue(
			answer({ portal_chat_enabled: true, daily_message_limit: 200, user_daily_message_limit: 50, version: 2 })
		)
		const wrapper = await render()
		expect(disabled(wrapper, "portal-chat-switch")).toBe(true)
		expect(disabled(wrapper, "portal-chat-log-search-switch")).toBe(true)
		expect(wrapper.find("[data-testid=portal-chat-save]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=portal-chat-read-only]").text()).toContain("Only administrators")
	})

	it("reads the settings again when the AI reports above are turned off (the chat follows)", async () => {
		getCustomerPortalChatSettings.mockResolvedValue(answer({ portal_chat_enabled: true, daily_message_limit: 200 }))
		const Host = defineComponent({
			props: { ai: { type: Boolean, default: true } },
			setup: props => () =>
				h(NMessageProvider, () => h(PortalChatSettings, { customerCode: "ACME", aiReportsEnabled: props.ai }))
		})
		const wrapper = mount(Host)
		await flushPromises()
		expect(getCustomerPortalChatSettings).toHaveBeenCalledTimes(1)
		getCustomerPortalChatSettings.mockResolvedValue(
			answer({ portal_chat_enabled: false, daily_message_limit: 200 }, false)
		)
		await wrapper.setProps({ ai: false })
		await flushPromises()
		expect(getCustomerPortalChatSettings).toHaveBeenCalledTimes(2)
		expect(wrapper.get("[data-testid=portal-chat-state]").text()).toContain("Turn on the AI findings above first")
	})

	it("shows the server's refusal text", async () => {
		getCustomerPortalChatSettings.mockResolvedValue(answer())
		setCustomerPortalChatSettings.mockRejectedValue({
			response: {
				status: 422,
				data: {
					detail: "portal chat can only be turned on while the customer's AI reports are on",
					code: "invalid_request"
				}
			}
		})
		const wrapper = await render()
		await switchOf(wrapper, "portal-chat-log-search-switch").trigger("click")
		await wrapper.get("[data-testid=portal-chat-save]").trigger("click")
		await flushPromises()
		expect(document.body.textContent).toContain(
			"portal chat can only be turned on while the customer's AI reports are on"
		)
	})
})
