import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import IocEnrichmentSettings from "../IocEnrichmentSettings.vue"

const getCustomerIocEnrichmentSettings = vi.fn()
const setCustomerIocEnrichmentSettings = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		customerPortal: {
			getCustomerIocEnrichmentSettings: (...args: unknown[]) => getCustomerIocEnrichmentSettings(...args),
			setCustomerIocEnrichmentSettings: (...args: unknown[]) => setCustomerIocEnrichmentSettings(...args)
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))
const formatDate = vi.hoisted(() =>
	vi.fn((date: string, _format: string, opts?: { tz?: boolean }) => `${date}${opts?.tz ? " local" : ""}`)
)
vi.mock("@/utils/format", () => ({ formatDate }))

function settings(
	enabled: boolean,
	{
		updatedAt = null,
		limit = null,
		connectors = { virustotal: true, opencti: true },
		cacheHours = 24
	}: {
		updatedAt?: string | null
		limit?: number | null
		connectors?: { virustotal: boolean; opencti: boolean }
		cacheHours?: number
	} = {}
) {
	return {
		data: {
			success: true,
			message: "",
			settings: {
				customer_code: "ACME",
				enabled,
				daily_lookup_limit: limit,
				updated_at: updatedAt,
				updated_by: updatedAt ? 1 : null
			},
			connectors,
			cache_hours: cacheHours
		}
	}
}

function render() {
	const Host = defineComponent({
		render: () => h(NMessageProvider, () => h(IocEnrichmentSettings, { customerCode: "ACME" }))
	})
	return mount(Host)
}

beforeEach(() => {
	getCustomerIocEnrichmentSettings.mockReset()
	setCustomerIocEnrichmentSettings.mockReset()
	formatDate.mockClear()
	auth.isAdmin = true
})

/** Customers → Customer → IOC Enrichment (#1318). */
describe("customer portal ioc enrichment settings", () => {
	it("reads the switch as off until the customer has opted in", async () => {
		getCustomerIocEnrichmentSettings.mockResolvedValue(settings(false))
		const wrapper = render()
		await flushPromises()
		expect(getCustomerIocEnrichmentSettings).toHaveBeenCalledWith("ACME")
		expect(wrapper.get("[data-testid=ioc-enrichment-settings-state]").text()).toContain("cannot check IOCs")
		expect(wrapper.find("[data-testid=ioc-enrichment-settings-limit]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=ioc-enrichment-settings-readonly]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=ioc-enrichment-settings-updated]").exists()).toBe(false)
	})

	it("lets an admin turn it on", async () => {
		getCustomerIocEnrichmentSettings.mockResolvedValue(settings(false))
		setCustomerIocEnrichmentSettings.mockResolvedValue(settings(true, { updatedAt: "2026-10-28T08:00:00" }))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=ioc-enrichment-settings-switch]").trigger("click")
		await flushPromises()
		expect(setCustomerIocEnrichmentSettings).toHaveBeenCalledWith("ACME", { enabled: true, daily_lookup_limit: null })
		expect(wrapper.get("[data-testid=ioc-enrichment-settings-state]").text()).toContain("can check the IOCs")
		expect(wrapper.get("[data-testid=ioc-enrichment-settings-updated]").text()).toBe(
			"Last changed 2026-10-28T08:00:00 local"
		)
	})

	it("is read-only for an analyst", async () => {
		auth.isAdmin = false
		getCustomerIocEnrichmentSettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=ioc-enrichment-settings-readonly]").exists()).toBe(true)
		expect(wrapper.get("[data-testid=ioc-enrichment-settings-switch]").classes()).toContain("n-switch--disabled")
		expect(wrapper.find("[data-testid=ioc-enrichment-settings-limit-save]").exists()).toBe(false)
	})

	it("says which source's connector is verified", async () => {
		getCustomerIocEnrichmentSettings.mockResolvedValue(
			settings(true, { connectors: { virustotal: true, opencti: false } })
		)
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=ioc-enrichment-settings-source-virustotal]").text()).toContain(
			"connector verified"
		)
		expect(wrapper.get("[data-testid=ioc-enrichment-settings-source-opencti]").text()).toContain("not verified")
		expect(wrapper.find("[data-testid=ioc-enrichment-settings-no-source]").exists()).toBe(false)
	})

	it("warns when it is on and no source can be asked", async () => {
		getCustomerIocEnrichmentSettings.mockResolvedValue(
			settings(true, { connectors: { virustotal: false, opencti: false } })
		)
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=ioc-enrichment-settings-no-source]").text()).toContain("No source can be asked")
	})

	it("tells how long an answer is kept, from the backend", async () => {
		getCustomerIocEnrichmentSettings.mockResolvedValue(settings(true, { cacheHours: 72 }))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=ioc-enrichment-settings-cache]").text()).toContain("kept 72 hours")
	})

	it("reads its help without a space before any punctuation", async () => {
		getCustomerIocEnrichmentSettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=ioc-enrichment-settings-help]").text()).not.toMatch(/\s[.,;:]/)
	})

	it("keeps the switch off when saving fails", async () => {
		getCustomerIocEnrichmentSettings.mockResolvedValue(settings(false))
		setCustomerIocEnrichmentSettings.mockRejectedValue(new Error("boom"))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=ioc-enrichment-settings-switch]").trigger("click")
		await flushPromises()
		expect(wrapper.get("[data-testid=ioc-enrichment-settings-state]").text()).toContain("cannot check IOCs")
	})
})

describe("customer portal ioc enrichment settings: the daily limit", () => {
	it("saves a limit with its own button, keeping the switch on", async () => {
		getCustomerIocEnrichmentSettings.mockResolvedValue(settings(true))
		setCustomerIocEnrichmentSettings.mockResolvedValue(settings(true, { updatedAt: "2026-10-28T08:00:00", limit: 250 }))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=ioc-enrichment-settings-limit-save]").exists()).toBe(false)
		await wrapper.get("[data-testid=ioc-enrichment-settings-limit-mode] input[value=limited]").setValue(true)
		await flushPromises()
		const input = wrapper.get("[data-testid=ioc-enrichment-settings-limit-value] input")
		await input.setValue("250")
		await input.trigger("blur")
		await flushPromises()
		await wrapper.get("[data-testid=ioc-enrichment-settings-limit-save]").trigger("click")
		await flushPromises()
		expect(setCustomerIocEnrichmentSettings).toHaveBeenCalledWith("ACME", { enabled: true, daily_lookup_limit: 250 })
		expect(wrapper.find("[data-testid=ioc-enrichment-settings-limit-save]").exists()).toBe(false)
	})

	it("keeps the stored limit when the switch is turned off and hides the limit", async () => {
		getCustomerIocEnrichmentSettings.mockResolvedValue(settings(true, { limit: 40 }))
		setCustomerIocEnrichmentSettings.mockResolvedValue(settings(false, { updatedAt: "2026-10-28T08:00:00", limit: 40 }))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=ioc-enrichment-settings-switch]").trigger("click")
		await flushPromises()
		expect(setCustomerIocEnrichmentSettings).toHaveBeenCalledWith("ACME", { enabled: false, daily_lookup_limit: 40 })
		expect(wrapper.find("[data-testid=ioc-enrichment-settings-limit]").exists()).toBe(false)
	})
})
