import { afterEach, describe, expect, it } from "vitest"
import { EXTERNAL_LINK_DEFAULTS, getContactLink, getDocumentationLink } from "../index"

function setRuntimeConfig(config: CopilotRuntimeConfig | undefined) {
	window.__COPILOT_CONFIG__ = config
}

afterEach(() => {
	setRuntimeConfig(undefined)
})

describe("user-menu external links", () => {
	it("falls back to the shipped defaults when nothing overrides them", () => {
		expect(getDocumentationLink()).toEqual(EXTERNAL_LINK_DEFAULTS.documentation)
		expect(getContactLink()).toEqual(EXTERNAL_LINK_DEFAULTS.contact)
	})

	it("applies a runtime override", () => {
		setRuntimeConfig({
			contactLabel: "Report an issue on GitHub",
			contactUrl: "https://github.com/socfortress/CoPilot/issues"
		})

		expect(getContactLink()).toEqual({
			label: "Report an issue on GitHub",
			url: "https://github.com/socfortress/CoPilot/issues"
		})
	})

	it("overrides each entry independently", () => {
		setRuntimeConfig({ documentationUrl: "https://wiki.example.org/soc" })

		// url overridden, label kept; the contact entry is untouched
		expect(getDocumentationLink()).toEqual({
			label: EXTERNAL_LINK_DEFAULTS.documentation.label,
			url: "https://wiki.example.org/soc"
		})
		expect(getContactLink()).toEqual(EXTERNAL_LINK_DEFAULTS.contact)
	})

	it("rejects a non-http(s) url instead of rendering it", () => {
		// the runtime file is generated from container env, so a bad value must not become an href
		setRuntimeConfig({ contactUrl: "javascript:alert(1)" })
		expect(getContactLink().url).toBe(EXTERNAL_LINK_DEFAULTS.contact.url)

		setRuntimeConfig({ contactUrl: "not a url at all" })
		expect(getContactLink().url).toBe(EXTERNAL_LINK_DEFAULTS.contact.url)
	})

	it("ignores blank and whitespace-only values", () => {
		setRuntimeConfig({ contactLabel: "   ", contactUrl: "  " })
		expect(getContactLink()).toEqual(EXTERNAL_LINK_DEFAULTS.contact)
	})

	it("trims surrounding whitespace from accepted values", () => {
		setRuntimeConfig({ contactLabel: "  Support  ", contactUrl: "  https://support.example.org  " })

		expect(getContactLink()).toEqual({ label: "Support", url: "https://support.example.org" })
	})
})
