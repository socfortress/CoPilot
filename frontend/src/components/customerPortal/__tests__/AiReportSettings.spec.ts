import type { CustomerPortalAiReportSettings } from "@/types/customer-portal"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AiReportSettings from "../AiReportSettings.vue"

const getCustomerAiReportSettings = vi.fn()
const setCustomerAiReportSettings = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		customerPortal: {
			getCustomerAiReportSettings: (...args: unknown[]) => getCustomerAiReportSettings(...args),
			setCustomerAiReportSettings: (...args: unknown[]) => setCustomerAiReportSettings(...args)
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))

function settings(over: Partial<CustomerPortalAiReportSettings> = {}) {
	return {
		data: {
			success: true,
			message: "",
			settings: {
				customer_code: "ACME",
				enabled: true,
				allow_customer_requests: false,
				daily_request_limit: null,
				requests_last_24h: 0,
				updated_at: null,
				updated_by: null,
				...over
			}
		}
	}
}

async function render() {
	const Host = defineComponent({ render: () => h(NMessageProvider, () => h(AiReportSettings, { customerCode: "ACME" })) })
	const wrapper = mount(Host)
	await flushPromises()
	return wrapper
}

function switchDisabled(wrapper: Awaited<ReturnType<typeof render>>, testId: string) {
	return wrapper.get(`[data-testid=${testId}]`).classes().includes("n-switch--disabled")
}

beforeEach(() => {
	getCustomerAiReportSettings.mockReset()
	setCustomerAiReportSettings.mockReset()
	auth.isAdmin = true
})

describe("customer portal AI report settings", () => {
	it("offers requests only once the findings are visible to the customer", async () => {
		getCustomerAiReportSettings.mockResolvedValue(settings({ enabled: false }))
		const wrapper = await render()
		expect(switchDisabled(wrapper, "ai-requests-switch")).toBe(true)
		expect(wrapper.get("[data-testid=ai-requests-state]").text()).toContain("Turn on the AI findings above first")
		expect(wrapper.find("[data-testid=ai-requests-limit]").exists()).toBe(false)
	})

	it("lets an admin allow requests, sending the read switch as it is", async () => {
		getCustomerAiReportSettings.mockResolvedValue(settings())
		setCustomerAiReportSettings.mockResolvedValue(settings({ allow_customer_requests: true }))
		const wrapper = await render()
		expect(switchDisabled(wrapper, "ai-requests-switch")).toBe(false)

		await wrapper.get("[data-testid=ai-requests-switch]").trigger("click")
		await flushPromises()
		expect(setCustomerAiReportSettings).toHaveBeenCalledWith("ACME", { enabled: true, allow_customer_requests: true })
		expect(wrapper.get("[data-testid=ai-requests-state]").text()).toContain("can ask the AI Analyst")
		expect(wrapper.find("[data-testid=ai-requests-limit]").exists()).toBe(true)
	})

	it("shows the day's usage against the limit, or without one", async () => {
		getCustomerAiReportSettings.mockResolvedValue(settings({ allow_customer_requests: true, requests_last_24h: 1 }))
		let wrapper = await render()
		expect(wrapper.get("[data-testid=ai-requests-usage]").text()).toBe("1 request in the last 24 hours, no limit.")

		getCustomerAiReportSettings.mockResolvedValue(
			settings({ allow_customer_requests: true, daily_request_limit: 20, requests_last_24h: 7 })
		)
		wrapper = await render()
		expect(wrapper.get("[data-testid=ai-requests-usage]").text()).toBe("7 of 20 requests used in the last 24 hours.")
	})

	it("saves a limit with its own button, and unlimited as null", async () => {
		getCustomerAiReportSettings.mockResolvedValue(settings({ allow_customer_requests: true }))
		setCustomerAiReportSettings.mockResolvedValue(settings({ allow_customer_requests: true, daily_request_limit: 20 }))
		const wrapper = await render()
		expect(wrapper.find("[data-testid=ai-requests-limit-save]").exists()).toBe(false)

		await wrapper.get("[data-testid=ai-requests-limit-mode] input[value=limited]").setValue(true)
		await flushPromises()
		expect(wrapper.find("[data-testid=ai-requests-limit-value]").exists()).toBe(true)
		await wrapper.get("[data-testid=ai-requests-limit-save]").trigger("click")
		await flushPromises()
		expect(setCustomerAiReportSettings).toHaveBeenLastCalledWith("ACME", { enabled: true, daily_request_limit: 20 })
		expect(wrapper.find("[data-testid=ai-requests-limit-save]").exists()).toBe(false)

		setCustomerAiReportSettings.mockResolvedValue(settings({ allow_customer_requests: true, daily_request_limit: null }))
		await wrapper.get("[data-testid=ai-requests-limit-mode] input[value=unlimited]").setValue(true)
		await flushPromises()
		await wrapper.get("[data-testid=ai-requests-limit-save]").trigger("click")
		await flushPromises()
		expect(setCustomerAiReportSettings).toHaveBeenLastCalledWith("ACME", { enabled: true, daily_request_limit: null })
	})

	it("is read-only for an analyst", async () => {
		auth.isAdmin = false
		getCustomerAiReportSettings.mockResolvedValue(settings({ allow_customer_requests: true, daily_request_limit: 5 }))
		const wrapper = await render()
		expect(switchDisabled(wrapper, "ai-report-switch")).toBe(true)
		expect(switchDisabled(wrapper, "ai-requests-switch")).toBe(true)
		await wrapper.get("[data-testid=ai-requests-limit-mode] input[value=unlimited]").setValue(true)
		await flushPromises()
		expect(wrapper.find("[data-testid=ai-requests-limit-save]").exists()).toBe(false)
	})
})
