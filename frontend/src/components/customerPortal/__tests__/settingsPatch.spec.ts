import type { SettingsFields } from "../settingsPatch"
import { describe, expect, it } from "vitest"
import { buildSettingsPatch, parseLogoDataUrl } from "../settingsPatch"

const PNG = "data:image/png;base64,iVBORw0KGgo="
const GIF = "data:image/gif;base64,R0lGODlh"
const SAVED: SettingsFields = { title: "Acme SOC", logo: PNG, brand_color: "#112233" }

describe("buildSettingsPatch", () => {
	it("sends only a changed title, never the logo", () => {
		expect(buildSettingsPatch(SAVED, { ...SAVED, title: "Renamed" })).toEqual({ title: "Renamed" })
	})

	it("sends a new logo with its MIME type", () => {
		expect(buildSettingsPatch(SAVED, { ...SAVED, logo: GIF })).toEqual({
			logo_base64: "R0lGODlh",
			logo_mime_type: "image/gif"
		})
	})

	it("turns a cleared field into a reset", () => {
		expect(buildSettingsPatch(SAVED, { title: "", logo: null, brand_color: null })).toEqual({
			reset: ["title", "logo", "brand_color"]
		})
	})

	it("combines changes and resets", () => {
		expect(buildSettingsPatch(SAVED, { ...SAVED, title: "X", brand_color: null })).toEqual({
			title: "X",
			reset: ["brand_color"]
		})
	})

	it("returns null when nothing changed, whitespace included", () => {
		expect(buildSettingsPatch(SAVED, { ...SAVED })).toBeNull()
		expect(buildSettingsPatch(SAVED, { ...SAVED, title: "  Acme SOC " })).toBeNull()
		expect(buildSettingsPatch({ title: "", logo: null, brand_color: null }, { title: " ", logo: "", brand_color: "" })).toBeNull()
	})

	it("never sends an empty value, which the API rejects", () => {
		const patch = buildSettingsPatch(SAVED, { title: "  ", logo: "", brand_color: "" })
		expect(Object.values(patch ?? {}).filter(value => value === "" || value === null)).toEqual([])
	})
})

describe("parseLogoDataUrl", () => {
	it("splits a data URL", () => {
		expect(parseLogoDataUrl(PNG)).toEqual({ mime_type: "image/png", base64: "iVBORw0KGgo=" })
	})

	it("rejects anything else", () => {
		expect(parseLogoDataUrl(null)).toBeNull()
		expect(parseLogoDataUrl("iVBORw0KGgo=")).toBeNull()
	})
})
