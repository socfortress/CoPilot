import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import Form from "../Form.vue"
import Settings from "../Settings.vue"

const getSettings = vi.fn()
const patchSettings = vi.fn()
const getCustomerBranding = vi.fn()
const setCustomerBranding = vi.fn()

vi.mock("@/api", () => ({
	default: {
		customerPortal: {
			getSettings: (...args: unknown[]) => getSettings(...args),
			patchSettings: (...args: unknown[]) => patchSettings(...args),
			getCustomerBranding: (...args: unknown[]) => getCustomerBranding(...args),
			setCustomerBranding: (...args: unknown[]) => setCustomerBranding(...args),
			deleteCustomerBranding: vi.fn()
		}
	}
}))
vi.mock("@/components/common/ImageCropper.vue", () => ({ default: defineComponent({ render: () => null }) }))

function globalSettings(over: Record<string, unknown> = {}) {
	return {
		data: {
			success: true,
			message: "",
			settings: {
				id: 1,
				title: "SOC",
				logo_base64: null,
				logo_mime_type: null,
				brand_color: "#215ac8",
				theme_from_brand_color: false,
				updated_at: "2026-10-19T10:00:00",
				...over
			}
		}
	}
}

function customerBranding(override: Record<string, unknown> | null, effective: Record<string, unknown> = {}) {
	return {
		data: {
			success: true,
			message: "",
			override: override && {
				id: 1,
				customer_code: "ACME",
				enabled: true,
				title: null,
				logo_base64: null,
				logo_mime_type: null,
				brand_color: null,
				theme_from_brand_color: null,
				updated_at: "",
				updated_by: 1,
				...override
			},
			effective: {
				title: "SOC",
				logo_base64: null,
				logo_mime_type: null,
				brand_color: "#215ac8",
				theme_from_brand_color: false,
				source: override ? "custom" : "global",
				customer_code: override ? "ACME" : null,
				...effective
			}
		}
	}
}

function render(component: typeof Form | typeof Settings, props: Record<string, unknown> = {}) {
	const Host = defineComponent({ render: () => h(NMessageProvider, () => h(component, props)) })
	return mount(Host, { attachTo: document.body })
}

function choose(wrapper: ReturnType<typeof render>, label: string) {
	const option = wrapper
		.get("[data-testid=portal-theme-choice]")
		.findAll("label")
		.find(item => item.text().startsWith(label))
	if (!option) throw new Error(`no "${label}" option`)
	return option.find("input").setValue(true)
}

beforeEach(() => {
	for (const fn of [getSettings, patchSettings, getCustomerBranding, setCustomerBranding]) fn.mockReset()
})

describe("global settings: theme the portal with the brand color (#1278)", () => {
	it("reads the stored choice and patches only the switch", async () => {
		getSettings.mockResolvedValue(globalSettings())
		patchSettings.mockResolvedValue(globalSettings({ theme_from_brand_color: true }))
		const wrapper = render(Form)
		await flushPromises()

		const toggle = wrapper.get("[data-testid=portal-theme-switch]")
		expect(toggle.attributes("aria-checked")).toBe("false")
		expect(wrapper.find("[data-testid=portal-theme-choice]").exists()).toBe(false)

		await toggle.trigger("click")
		await wrapper.get("[data-testid=portal-settings-save]").trigger("click")
		await flushPromises()
		expect(patchSettings).toHaveBeenCalledWith({ theme_from_brand_color: true })
	})

	it("warns when it is on with no brand color to take", async () => {
		getSettings.mockResolvedValue(globalSettings({ brand_color: null, theme_from_brand_color: true }))
		const wrapper = render(Form)
		await flushPromises()
		expect(wrapper.get("[data-testid=portal-theme-no-color]").text()).toContain("default theme")
	})

	it("shows the brand color on the preview's sign-in button only while it is on", async () => {
		getSettings.mockResolvedValue(globalSettings())
		const wrapper = render(Settings)
		await flushPromises()
		const button = () => wrapper.get("[data-testid=portal-preview-sign-in]").element as HTMLElement
		expect(button().style.backgroundColor).toBe("")

		await wrapper.get("[data-testid=portal-theme-switch]").trigger("click")
		await flushPromises()
		expect(button().style.backgroundColor).toBe("rgb(33, 90, 200)")
		expect(button().style.color).toBe("rgb(255, 255, 255)")
	})
})

describe("a customer's branding: inherit, on or off (#1278)", () => {
	it("shows the inherited global choice and sends null for it", async () => {
		getSettings.mockResolvedValue(globalSettings({ theme_from_brand_color: true }))
		getCustomerBranding.mockResolvedValue(customerBranding({ title: "Acme" }))
		setCustomerBranding.mockResolvedValue(customerBranding({ title: "Acme" }))
		const wrapper = render(Form, { customerCode: "ACME" })
		await flushPromises()

		const choice = wrapper.get("[data-testid=portal-theme-choice]")
		expect(choice.text()).toContain("Inherit · On")
		expect(wrapper.find("[data-testid=portal-theme-switch]").exists()).toBe(false)

		await wrapper.get("[data-testid=portal-settings-save]").trigger("click")
		await flushPromises()
		expect(setCustomerBranding).toHaveBeenCalledWith(
			"ACME",
			expect.objectContaining({ theme_from_brand_color: null })
		)
	})

	it.each([
		["On", true],
		["Off", false]
	])("sends %s as the customer's own choice", async (label, value) => {
		getSettings.mockResolvedValue(globalSettings())
		getCustomerBranding.mockResolvedValue(customerBranding({}))
		setCustomerBranding.mockResolvedValue(customerBranding({ theme_from_brand_color: value }))
		const wrapper = render(Form, { customerCode: "ACME" })
		await flushPromises()

		await choose(wrapper, label)
		await wrapper.get("[data-testid=portal-settings-save]").trigger("click")
		await flushPromises()
		expect(setCustomerBranding).toHaveBeenCalledWith(
			"ACME",
			expect.objectContaining({ enabled: true, theme_from_brand_color: value })
		)
	})

	it("reads a stored choice back", async () => {
		getSettings.mockResolvedValue(globalSettings({ theme_from_brand_color: true }))
		getCustomerBranding.mockResolvedValue(customerBranding({ theme_from_brand_color: false }))
		const wrapper = render(Form, { customerCode: "ACME" })
		await flushPromises()
		const checked = wrapper.get("[data-testid=portal-theme-choice]").find("input:checked")
		expect(checked.element.closest("label")?.textContent?.trim()).toBe("Off")
	})
})
