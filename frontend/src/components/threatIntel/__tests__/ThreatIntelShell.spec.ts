/**
 * Threat Intel page (#1153): one page with a tab per source. OpenCTI is a tab
 * only for a verified connector, and /opencti (its old page) must land on it.
 */

import type { RouteLocationNormalized } from "vue-router"
import { mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { reactive, ref } from "vue"
import { threatIntelRoutes } from "@/router/routes/threat-intel"
import ThreatIntelShell from "../ThreatIntelShell.vue"

const available = ref(false)
const loaded = ref(true)
const route = reactive<{ query: Record<string, string> }>({ query: {} })
const replace = vi.fn()

vi.mock("@/composables/useOpenCTIAvailability", () => ({
	useOpenCTIAvailability: () => ({ available, loaded, refresh: () => Promise.resolve() })
}))

vi.mock("vue-router", async importOriginal => ({
	...(await importOriginal<typeof import("vue-router")>()),
	useRoute: () => route,
	useRouter: () => ({ replace })
}))

async function mountShell(query: Record<string, string> = {}) {
	route.query = query
	const wrapper = mount(ThreatIntelShell, {
		global: {
			stubs: {
				ThreatIntelForm: { template: "<div data-test='socfortress' />" },
				VirusTotalForm: { template: "<div data-test='virustotal' />" },
				OpenCTIPanel: { template: "<div data-test='opencti' />" },
				Icon: true,
				RouterLink: { template: "<a><slot /></a>" }
			}
		}
	})
	await new Promise(resolve => setTimeout(resolve, 0))
	return wrapper
}

describe("threat intel page", () => {
	beforeEach(() => {
		available.value = false
		loaded.value = true
		replace.mockReset()
	})

	it("opens on SOCFortress and always offers VirusTotal", async () => {
		const wrapper = await mountShell()
		expect(wrapper.find("[data-test='socfortress']").exists()).toBe(true)
		expect(wrapper.text()).toContain("VirusTotal")
	})

	it("offers OpenCTI only for a verified connector", async () => {
		expect((await mountShell()).text()).not.toContain("OpenCTI")
		available.value = true
		expect((await mountShell()).text()).toContain("OpenCTI")
	})

	it("opens the OpenCTI tab from the URL", async () => {
		available.value = true
		const wrapper = await mountShell({ tab: "opencti" })
		expect(wrapper.find("[data-test='opencti']").exists()).toBe(true)
		expect(wrapper.text()).not.toContain("OpenCTI is not configured")
	})

	it("explains a link to OpenCTI on a deployment without it, instead of a blank tab", async () => {
		const wrapper = await mountShell({ tab: "opencti" })
		expect(wrapper.text()).toContain("OpenCTI is not configured")
		expect(wrapper.find("[data-test='socfortress']").exists()).toBe(true)
		expect(wrapper.find("[data-test='opencti']").exists()).toBe(false)
	})

	it("ignores an unknown tab", async () => {
		const wrapper = await mountShell({ tab: "nonsense" })
		expect(wrapper.find("[data-test='socfortress']").exists()).toBe(true)
	})
})

describe("/opencti", () => {
	const record = threatIntelRoutes.find(r => r.path === "/opencti")
	const redirect = record?.redirect as (to: Partial<RouteLocationNormalized>) => unknown

	it("lands on the Threat Intel page's OpenCTI tab", () => {
		expect(redirect({ query: {} })).toEqual({ name: "ThreatIntel", query: { tab: "opencti" } })
	})

	it("keeps the sub-view an old bookmark asked for", () => {
		// The old page kept its sub-view in ?tab=; it's ?view= on the OpenCTI tab.
		expect(redirect({ query: { tab: "indicators" } })).toEqual({
			name: "ThreatIntel",
			query: { view: "indicators", tab: "opencti" }
		})
		expect(redirect({ query: { tab: "bogus" } })).toEqual({ name: "ThreatIntel", query: { tab: "opencti" } })
	})
})
