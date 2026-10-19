import type { EffectivePortalBranding, PortalSettings } from "@/types/portal"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { usePortalSettingsStore } from "../portalSettings"

vi.mock("@/api", () => ({ default: {} }))

function settings(fields: Partial<PortalSettings>): PortalSettings {
	return { id: 1, title: "SOC", logo_url: null, logo_mime_type: null, brand_color: null, updated_at: null, ...fields }
}

function branding(fields: Partial<EffectivePortalBranding>): EffectivePortalBranding {
	return {
		title: "Acme",
		logo_url: null,
		logo_mime_type: null,
		brand_color: null,
		source: "custom",
		customer_code: "ACME",
		...fields
	}
}

/** The brand color the interface takes as its primary (#1278): only when CoPilot turned that on. */
describe("themeBrandColor", () => {
	beforeEach(() => setActivePinia(createPinia()))

	it("is null until CoPilot turns it on", () => {
		const store = usePortalSettingsStore()
		expect(store.themeBrandColor).toBeNull()
		store.settings = settings({ brand_color: "#215ac8" })
		expect(store.themeBrandColor).toBeNull()
		store.settings = settings({ brand_color: "#215ac8", theme_from_brand_color: false })
		expect(store.themeBrandColor).toBeNull()
	})

	it("is the global color on the login page when the global choice is on", () => {
		const store = usePortalSettingsStore()
		store.settings = settings({ brand_color: "#215ac8", theme_from_brand_color: true })
		expect(store.themeBrandColor).toBe("#215ac8")
	})

	it("follows the signed-in customer's branding, either way", () => {
		const store = usePortalSettingsStore()
		store.settings = settings({ brand_color: "#215ac8", theme_from_brand_color: true })
		store.branding = branding({ brand_color: "#0f766e", theme_from_brand_color: false })
		expect(store.themeBrandColor).toBeNull()
		store.branding = branding({ brand_color: "#0f766e", theme_from_brand_color: true })
		expect(store.themeBrandColor).toBe("#0f766e")
	})

	it("goes back to the global choice when the branding is cleared at logout", () => {
		const store = usePortalSettingsStore()
		store.settings = settings({ brand_color: "#215ac8", theme_from_brand_color: false })
		store.branding = branding({ brand_color: "#0f766e", theme_from_brand_color: true })
		store.clearBranding()
		expect(store.themeBrandColor).toBeNull()
	})

	it("keeps the default theme without a color, or with one that isn't a hex color", () => {
		const store = usePortalSettingsStore()
		store.branding = branding({ brand_color: null, theme_from_brand_color: true })
		expect(store.themeBrandColor).toBeNull()
		store.branding = branding({ brand_color: "javascript:alert(1)", theme_from_brand_color: true })
		expect(store.themeBrandColor).toBeNull()
	})
})
