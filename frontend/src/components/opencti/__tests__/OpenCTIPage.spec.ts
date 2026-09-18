/**
 * The OpenCTI page (#1147) must stay out of the way on deployments without a
 * verified OpenCTI connector: no Tools entry, and a clear "not configured"
 * state (not an error toast) if someone lands on /opencti directly.
 */

import { mount } from "@vue/test-utils"
import { describe, expect, it, vi } from "vitest"
import { ref } from "vue"
import { getInvestigateItem } from "@/app-layouts/common/Navbar/items/investigate"
import OpenCTIShell from "../OpenCTIShell.vue"
import { markingType, scoreColor, scoreTagType } from "../utils"

const available = ref(false)
const loaded = ref(true)

vi.mock("@/composables/useOpenCTIAvailability", () => ({
	useOpenCTIAvailability: () => ({
		available,
		loaded,
		refresh: () => Promise.resolve(),
		objectUrl: () => null
	})
}))

vi.mock("vue-router", async importOriginal => ({
	...(await importOriginal<typeof import("vue-router")>()),
	useRoute: () => ({ query: {} }),
	useRouter: () => ({ replace: vi.fn() })
}))

function childKeys(showOpenCTI: boolean): unknown[] {
	const item = getInvestigateItem(showOpenCTI) as { children?: { key?: unknown }[] }
	return (item.children || []).map(child => child.key)
}

describe("investigate menu", () => {
	it("lists OpenCTI only for a verified connector", () => {
		expect(childKeys(true)).toContain("OpenCTI")
		expect(childKeys(false)).not.toContain("OpenCTI")
	})

	it("leaves the rest of the menu unchanged", () => {
		expect(childKeys(true).filter(key => key !== "OpenCTI")).toEqual(childKeys(false))
	})
})

describe("openCTI page", () => {
	async function mountShell() {
		const wrapper = mount(OpenCTIShell, {
			global: {
				stubs: {
					OpenCTIPlatformStats: { template: "<div data-test='stats' />" },
					OpenCTIForm: true,
					OpenCTIIndicatorsIndex: true,
					Icon: true,
					RouterLink: { template: "<a><slot /></a>" }
				}
			}
		})
		await new Promise(resolve => setTimeout(resolve, 0))
		return wrapper
	}

	it("explains how to configure OpenCTI instead of loading anything", async () => {
		available.value = false
		const wrapper = await mountShell()
		expect(wrapper.text()).toContain("OpenCTI is not configured")
		expect(wrapper.find("[data-test='stats']").exists()).toBe(false)
	})

	it("shows the stats and tabs for a verified connector", async () => {
		available.value = true
		const wrapper = await mountShell()
		expect(wrapper.text()).not.toContain("OpenCTI is not configured")
		expect(wrapper.find("[data-test='stats']").exists()).toBe(true)
		expect(wrapper.text()).toContain("IOC Lookup")
		expect(wrapper.text()).toContain("Indicators")
	})
})

describe("score and marking helpers", () => {
	it.each([
		[null, undefined, "default"],
		[40, undefined, "default"],
		[50, "warning", "warning"],
		[75, "danger", "error"],
		[100, "danger", "error"]
	] as const)("score %s", (score, badge, tag) => {
		expect(scoreColor(score)).toBe(badge)
		expect(scoreTagType(score)).toBe(tag)
	})

	it.each([
		["TLP:RED", "error"],
		["TLP:AMBER+STRICT", "warning"],
		["tlp:green", "success"],
		["TLP:CLEAR", "default"],
		["PAP:WHITE", "default"]
	] as const)("marking %s", (marking, type) => {
		expect(markingType(marking)).toBe(type)
	})
})
