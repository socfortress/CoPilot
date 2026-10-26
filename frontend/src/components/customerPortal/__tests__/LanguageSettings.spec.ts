import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import LanguageSettings from "../LanguageSettings.vue"
import { normalizeLanguages, PORTAL_LANGUAGES, sameLanguages } from "../portalLanguages"

const getCustomerLanguageSettings = vi.fn()
const setCustomerLanguageSettings = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		customerPortal: {
			getCustomerLanguageSettings: (...args: unknown[]) => getCustomerLanguageSettings(...args),
			setCustomerLanguageSettings: (...args: unknown[]) => setCustomerLanguageSettings(...args)
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "YYYY-MM-DD HH:mm" } }) }))
const formatDate = vi.hoisted(() =>
	vi.fn((date: string, _format: string, opts?: { tz?: boolean }) => `${date}${opts?.tz ? " local" : ""}`)
)
vi.mock("@/utils/format", () => ({ formatDate }))

function settings(languages: string[], updatedAt: string | null = null) {
	return {
		data: {
			success: true,
			message: "",
			supported: [...PORTAL_LANGUAGES],
			settings: { customer_code: "ACME", languages, updated_at: updatedAt, updated_by: updatedAt ? 1 : null }
		}
	}
}

function render() {
	const Host = defineComponent({
		render: () => h(NMessageProvider, () => h(LanguageSettings, { customerCode: "ACME" }))
	})
	return mount(Host)
}

function checkbox(wrapper: ReturnType<typeof render>, code: string) {
	return wrapper.get(`[data-testid=language-settings-${code}] .n-checkbox`)
}

function isChecked(wrapper: ReturnType<typeof render>, code: string) {
	return checkbox(wrapper, code).classes().includes("n-checkbox--checked")
}

beforeEach(() => {
	getCustomerLanguageSettings.mockReset()
	setCustomerLanguageSettings.mockReset()
	formatDate.mockClear()
	auth.isAdmin = true
})

/** Customers → Customer → Portal Languages (#1310). */
describe("customer portal language settings", () => {
	it("lists every portal language, English on and locked as the default", async () => {
		getCustomerLanguageSettings.mockResolvedValue(settings(["en"]))
		const wrapper = render()
		await flushPromises()
		expect(getCustomerLanguageSettings).toHaveBeenCalledWith("ACME")
		for (const code of PORTAL_LANGUAGES) expect(wrapper.find(`[data-testid=language-settings-${code}]`).exists()).toBe(true)
		expect(isChecked(wrapper, "en")).toBe(true)
		expect(checkbox(wrapper, "en").classes()).toContain("n-checkbox--disabled")
		expect(wrapper.get("[data-testid=language-settings-en]").text()).toContain("Always on · default")
		expect(isChecked(wrapper, "it")).toBe(false)
		expect(wrapper.get("[data-testid=language-settings-it]").text()).toContain("Italiano")
		expect(wrapper.get("[data-testid=language-settings-cs]").text()).toContain("Čeština")
	})

	it("saves the whole set, English included, in the portal's order", async () => {
		getCustomerLanguageSettings.mockResolvedValue(settings(["en"]))
		setCustomerLanguageSettings.mockResolvedValue(settings(["en", "it", "cs"], "2026-10-26T08:00:00"))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=language-settings-save]").attributes("disabled")).toBeDefined()

		await checkbox(wrapper, "cs").trigger("click")
		await checkbox(wrapper, "it").trigger("click")
		expect(wrapper.find("[data-testid=language-settings-unsaved]").exists()).toBe(true)
		await wrapper.get("[data-testid=language-settings-save]").trigger("click")
		await flushPromises()

		expect(setCustomerLanguageSettings).toHaveBeenCalledWith("ACME", { languages: ["en", "it", "cs"] })
		expect(wrapper.find("[data-testid=language-settings-unsaved]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=language-settings-updated]").text()).toBe("Last changed 2026-10-26T08:00:00 local")
	})

	it("never lets English be turned off", async () => {
		getCustomerLanguageSettings.mockResolvedValue(settings(["en", "de"]))
		const wrapper = render()
		await flushPromises()
		await checkbox(wrapper, "en").trigger("click")
		expect(isChecked(wrapper, "en")).toBe(true)
		expect(wrapper.find("[data-testid=language-settings-unsaved]").exists()).toBe(false)
	})

	it("puts back what is stored on Reset", async () => {
		getCustomerLanguageSettings.mockResolvedValue(settings(["en", "fr"]))
		const wrapper = render()
		await flushPromises()
		await checkbox(wrapper, "fr").trigger("click")
		expect(isChecked(wrapper, "fr")).toBe(false)
		await wrapper.get("[data-testid=language-settings-reset]").trigger("click")
		expect(isChecked(wrapper, "fr")).toBe(true)
		expect(setCustomerLanguageSettings).not.toHaveBeenCalled()
	})

	it("keeps the choice unsaved when saving fails", async () => {
		getCustomerLanguageSettings.mockResolvedValue(settings(["en"]))
		setCustomerLanguageSettings.mockRejectedValue(new Error("boom"))
		const wrapper = render()
		await flushPromises()
		await checkbox(wrapper, "nl").trigger("click")
		await wrapper.get("[data-testid=language-settings-save]").trigger("click")
		await flushPromises()
		expect(isChecked(wrapper, "nl")).toBe(true)
		expect(wrapper.find("[data-testid=language-settings-unsaved]").exists()).toBe(true)
	})

	it("is read-only for an analyst", async () => {
		auth.isAdmin = false
		getCustomerLanguageSettings.mockResolvedValue(settings(["en", "it"]))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=language-settings-readonly]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=language-settings-save]").exists()).toBe(false)
		expect(checkbox(wrapper, "de").classes()).toContain("n-checkbox--disabled")
		await checkbox(wrapper, "de").trigger("click")
		expect(isChecked(wrapper, "de")).toBe(false)
	})

	it("says how users pick and what stays untranslated, without a space before punctuation", async () => {
		getCustomerLanguageSettings.mockResolvedValue(settings(["en"]))
		const wrapper = render()
		await flushPromises()
		const help = wrapper.get("[data-testid=language-settings-help]").text()
		expect(help).toContain("avatar menu or their Profile")
		expect(help).toContain("at least one of them")
		expect(help).toMatch(/stay as they were written/)
		expect(help).not.toMatch(/\s[.,;:]/)
	})
})

describe("portal language sets", () => {
	it("are normalised to known codes, the portal's order and English first", () => {
		expect(normalizeLanguages(["cs", "xx", "it"])).toEqual(["en", "it", "cs"])
		expect(normalizeLanguages([])).toEqual(["en"])
	})

	it("compare as sets", () => {
		expect(sameLanguages(["it", "en"], ["en", "it"])).toBe(true)
		expect(sameLanguages(["it"], ["en", "it"])).toBe(true)
		expect(sameLanguages(["en", "de"], ["en", "it"])).toBe(false)
	})
})
