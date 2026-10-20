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

function choose(wrapper: ReturnType<typeof render>, value: "inherit" | "on" | "off") {
	return wrapper.get(`[data-testid=portal-theme-${value}] input`).setValue(true)
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
		const button = () => wrapper.get("[data-testid=portal-preview-sign-in]").element as HTMLButtonElement
		// Off: the portal's own default primary, as customers see it.
		expect(button().style.backgroundColor).toBe("rgb(219, 157, 0)")
		// Enabled, as the portal shows it: a disabled one is faded and misstates the color.
		expect(button().disabled).toBe(false)

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

		const inherit = wrapper.get("[data-testid=portal-theme-inherit]")
		expect(inherit.text()).toContain("Same as the global setting")
		expect(inherit.text()).toContain("Currently on")
		expect((inherit.find("input").element as HTMLInputElement).checked).toBe(true)
		expect(wrapper.find("[data-testid=portal-theme-switch]").exists()).toBe(false)

		await wrapper.get("[data-testid=portal-settings-save]").trigger("click")
		await flushPromises()
		expect(setCustomerBranding).toHaveBeenCalledWith(
			"ACME",
			expect.objectContaining({ theme_from_brand_color: null })
		)
	})

	it.each([
		["on", true],
		["off", false]
	] as const)("sends %s as the customer's own choice", async (choice, value) => {
		getSettings.mockResolvedValue(globalSettings())
		getCustomerBranding.mockResolvedValue(customerBranding({}))
		setCustomerBranding.mockResolvedValue(customerBranding({ theme_from_brand_color: value }))
		const wrapper = render(Form, { customerCode: "ACME" })
		await flushPromises()

		await choose(wrapper, choice)
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
		expect((wrapper.get("[data-testid=portal-theme-off] input").element as HTMLInputElement).checked).toBe(true)
		expect(wrapper.get("[data-testid=portal-theme-off]").text()).toContain("Keep the default theme")
		expect(wrapper.get("[data-testid=portal-theme-inherit]").text()).toContain("Currently on")
	})
})
