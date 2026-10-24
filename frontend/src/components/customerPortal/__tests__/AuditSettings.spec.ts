import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AuditSettings from "../AuditSettings.vue"

const getCustomerAuditSettings = vi.fn()
const setCustomerAuditSettings = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		customerPortal: {
			getCustomerAuditSettings: (...args: unknown[]) => getCustomerAuditSettings(...args),
			setCustomerAuditSettings: (...args: unknown[]) => setCustomerAuditSettings(...args)
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))
const formatDate = vi.hoisted(() =>
	vi.fn((date: string, _format: string, opts?: { tz?: boolean }) => `${date}${opts?.tz ? " local" : ""}`)
)
vi.mock("@/utils/format", () => ({ formatDate }))

function settings(enabled: boolean, updatedAt: string | null = null) {
	return {
		data: {
			success: true,
			message: "",
			settings: { customer_code: "ACME", enabled, updated_at: updatedAt, updated_by: updatedAt ? 1 : null }
		}
	}
}

function render() {
	const Host = defineComponent({
		render: () => h(NMessageProvider, () => h(AuditSettings, { customerCode: "ACME" }))
	})
	return mount(Host)
}

beforeEach(() => {
	getCustomerAuditSettings.mockReset()
	setCustomerAuditSettings.mockReset()
	formatDate.mockClear()
	auth.isAdmin = true
})

/** Customers → Customer → Audit Log (#1298). */
describe("customer portal audit log settings", () => {
	it("reads the switch as off until the customer has opted in", async () => {
		getCustomerAuditSettings.mockResolvedValue(settings(false))
		const wrapper = render()
		await flushPromises()
		expect(getCustomerAuditSettings).toHaveBeenCalledWith("ACME")
		expect(wrapper.get("[data-testid=audit-settings-state]").text()).toContain("Nobody at this customer")
		expect(wrapper.find("[data-testid=audit-settings-readonly]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=audit-settings-updated]").exists()).toBe(false)
	})

	it("lets an admin turn the page on", async () => {
		getCustomerAuditSettings.mockResolvedValue(settings(false))
		setCustomerAuditSettings.mockResolvedValue(settings(true, "2026-10-21T08:00:00"))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=audit-settings-switch]").trigger("click")
		await flushPromises()
		expect(setCustomerAuditSettings).toHaveBeenCalledWith("ACME", { enabled: true })
		expect(wrapper.get("[data-testid=audit-settings-state]").text()).toContain("administrators can see")
	})

	it("is read-only for an analyst", async () => {
		auth.isAdmin = false
		getCustomerAuditSettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=audit-settings-readonly]").exists()).toBe(true)
		expect(wrapper.get("[data-testid=audit-settings-switch]").classes()).toContain("n-switch--disabled")
	})

	it("shows when it last changed in the viewer's time, the stored time being UTC", async () => {
		getCustomerAuditSettings.mockResolvedValue(settings(true, "2026-10-21T08:00:00"))
		const wrapper = render()
		await flushPromises()
		expect(formatDate).toHaveBeenCalledWith("2026-10-21T08:00:00", "YYYY-MM-DD HH:mm", { tz: true })
		expect(wrapper.get("[data-testid=audit-settings-updated]").text()).toBe(
			"Last changed 2026-10-21T08:00:00 local"
		)
	})

	it("reads its help without a space before any punctuation", async () => {
		getCustomerAuditSettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=audit-settings-help]").text()).not.toMatch(/\s[.,;:]/)
	})

	it("keeps the switch off when saving fails", async () => {
		getCustomerAuditSettings.mockResolvedValue(settings(false))
		setCustomerAuditSettings.mockRejectedValue(new Error("boom"))
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=audit-settings-switch]").trigger("click")
		await flushPromises()
		expect(wrapper.get("[data-testid=audit-settings-state]").text()).toContain("Nobody at this customer")
	})
})

describe("customer portal audit log settings: what it promises", () => {
	it("says who reads it and that the SOC is never named", async () => {
		getCustomerAuditSettings.mockResolvedValue(settings(true))
		const wrapper = render()
		await flushPromises()
		const help = wrapper.get("[data-testid=audit-settings-help]").text()
		expect(help).toContain("customer administrators")
		expect(help).toContain("Security")
		expect(help).toMatch(/without an analyst's name or address/)
		expect(help).toMatch(/Comment text is never shown/)
	})
})
