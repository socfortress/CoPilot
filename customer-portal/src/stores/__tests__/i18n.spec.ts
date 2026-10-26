import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import i18n from "@/lang"
import { browserLocale, useLocalesStore } from "../i18n"

const languages = vi.hoisted(() => ({ setMine: vi.fn() }))
vi.mock("@/api", () => ({ default: { languages } }))

beforeEach(() => {
	setActivePinia(createPinia())
	languages.setMine.mockReset()
	i18n.global.locale.value = "en"
	document.documentElement.lang = ""
})

/** The portal's language (#1310). */
describe("the portal's language", () => {
	it("starts in English, with English only", () => {
		const store = useLocalesStore()
		expect(store.locale).toBe("en")
		expect(store.available).toEqual(["en"])
		expect(store.canChoose).toBe(false)
	})

	it("takes the user's language and the ones their customers offer from the profile", () => {
		const store = useLocalesStore()
		store.applyProfile({ locale: "it", available_locales: ["en", "it", "nl"], locale_chosen: true })
		expect(store.available).toEqual(["en", "it", "nl"])
		expect(store.locale).toBe("it")
		expect(i18n.global.locale.value).toBe("it")
		expect(document.documentElement.lang).toBe("it")
		expect(store.naiveuiLocale.name).toBe("it-IT")
		expect(store.canChoose).toBe(true)
	})

	it("keeps English in the list and drops codes it doesn't ship", () => {
		const store = useLocalesStore()
		store.applyProfile({ locale: "jp", available_locales: ["it", "jp"], locale_chosen: true })
		expect(store.available).toEqual(["en", "it"])
		expect(store.locale).toBe("en")
	})

	it("uses the browser's language when nothing is picked and the customers offer it", () => {
		const nav = vi.spyOn(navigator, "languages", "get").mockReturnValue(["fr-FR", "de-DE"])
		const store = useLocalesStore()
		store.applyProfile({ locale: "en", available_locales: ["en", "de"], locale_chosen: false })
		expect(store.locale).toBe("de")
		// A pick wins over the browser.
		store.applyProfile({ locale: "en", available_locales: ["en", "de"], locale_chosen: true })
		expect(store.locale).toBe("en")
		nav.mockRestore()
	})

	it("stores the user's pick on the server, then shows it", async () => {
		languages.setMine.mockResolvedValue({ data: { locale: "it", available: ["en", "it"] } })
		const store = useLocalesStore()
		store.applyProfile({ locale: "en", available_locales: ["en", "it"], locale_chosen: true })
		await store.choose("it")
		expect(languages.setMine).toHaveBeenCalledWith("it")
		expect(store.locale).toBe("it")
		expect(store.saving).toBe(false)
	})

	it("never asks for a language the user may not pick, and keeps the current one when saving fails", async () => {
		const store = useLocalesStore()
		store.applyProfile({ locale: "en", available_locales: ["en", "it"], locale_chosen: true })
		await store.choose("de")
		expect(languages.setMine).not.toHaveBeenCalled()
		languages.setMine.mockRejectedValue(new Error("400"))
		await expect(store.choose("it")).rejects.toThrow("400")
		expect(store.locale).toBe("en")
		expect(store.saving).toBe(false)
	})

	it("goes back to English, English only, at logout", () => {
		const store = useLocalesStore()
		store.applyProfile({ locale: "it", available_locales: ["en", "it"], locale_chosen: true })
		store.reset()
		expect(store.locale).toBe("en")
		expect(store.available).toEqual(["en"])
		expect(i18n.global.locale.value).toBe("en")
	})
})

describe("the browser's language", () => {
	it("is the first one the user may pick, by its base code", () => {
		expect(browserLocale(["en", "it"], ["it-IT", "en-US"])).toBe("it")
		expect(browserLocale(["en", "nl"], ["fr-FR", "nl-BE"])).toBe("nl")
		expect(browserLocale(["en"], ["it-IT"])).toBeNull()
		expect(browserLocale(["en", "it"], [])).toBeNull()
	})
})
