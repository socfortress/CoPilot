/**
 * The customer page's grouped sections (#1325): which section a link opens, the URL on the
 * customer's own page only, sections mounted once and kept, the status lights read again on
 * leaving a section, pins and the hidden rail remembered per viewer.
 */
import type { CustomerSectionStatus } from "@/types/customers"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { computed, defineComponent, h, reactive, ref } from "vue"
import { routeLocationKey, routerKey } from "vue-router"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import CustomerDetailsTabs from "../CustomerDetailsTabs.vue"
import { statusFixture } from "../sections/__tests__/fixtures"
import { PINNED_KEY_PREFIX, RAIL_HIDDEN_KEY } from "../sections/useSectionPreferences"

const getSectionStatus = vi.fn()
const tabQuery = ref<string | undefined>(undefined)

vi.mock("@/api", () => ({
	default: {
		talonV2: { getAvailability: () => Promise.resolve({ data: { success: true, enabled: false } }) },
		customers: { getCustomerSectionStatus: (...a: unknown[]) => getSectionStatus(...a) }
	}
}))
vi.mock("@/composables/useNavigation", () => ({ useRouteQueryParam: () => computed(() => tabQuery.value) }))

// Each section's own component is replaced by a marker that counts its mounts.
const mounts: Record<string, number> = {}
function marker(name: string) {
	return {
		__esModule: true,
		default: defineComponent({
			setup() {
				mounts[name] = (mounts[name] ?? 0) + 1
				return () => h("div", { "data-marker": name })
			}
		})
	}
}
vi.mock("@/components/customers/provision/CustomerProvision.vue", () => marker("Provision"))
vi.mock("@/components/customers/security/CustomerSecurity.vue", () => marker("Security"))
vi.mock("@/components/customers/eventSources/CustomerEventSources.vue", () => marker("Event Sources"))
vi.mock("@/components/customerPortal/IocEnrichmentSettings.vue", () => marker("IOC Enrichment"))
vi.mock("@/components/customerPortal/Settings.vue", () => marker("Portal Branding"))
vi.mock("@/components/customers/integrations/CustomerIntegrations.vue", () => marker("3rd Party Integrations"))
vi.mock("@/components/customerPortal/SlaSettings.vue", () => marker("SLA"))

const router = { replace: vi.fn() }
const route = reactive<{ name: string; query: Record<string, string> }>({ name: "Customer", query: {} })

function render(options: { routeName?: string } = {}) {
	route.name = options.routeName ?? "Customer"
	return mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, () =>
					h(CustomerDetailsTabs, {
						customer: { customer_code: "ACME", customer_name: "Acme" } as never,
						customerInfo: null,
						customerMeta: null,
						customerPortainerStackId: null
					}))
		}),
		{ global: { provide: { [routerKey as symbol]: router, [routeLocationKey as symbol]: route } } }
	)
}

function signInAs(role: AuthUserRole, username = "ana") {
	useAuthStore().user = { access_token: "t", username, email: "", role }
}

async function settle() {
	await flushPromises()
	await vi.dynamicImportSettled()
	await flushPromises()
}

/** The pane shown: every other one is kept mounted under `display: none`. */
function visibleSection(wrapper: ReturnType<typeof render>): string | undefined {
	return wrapper
		.findAll("[data-section]")
		.find(pane => !(pane.attributes("style") ?? "").includes("display: none"))
		?.attributes("data-section")
}

function answered(status: CustomerSectionStatus | null = statusFixture()) {
	return { data: { success: true, customer_code: "ACME", sections: status } }
}

enableAutoUnmount(afterEach)

beforeEach(() => {
	setActivePinia(createPinia())
	signInAs(AuthUserRole.Admin)
	localStorage.clear()
	tabQuery.value = undefined
	route.query = {}
	router.replace.mockReset()
	for (const key of Object.keys(mounts)) delete mounts[key]
	getSectionStatus.mockReset().mockResolvedValue(answered())
})

describe("which section opens", () => {
	it("opens Info by default", async () => {
		const wrapper = render()
		await settle()
		expect(visibleSection(wrapper)).toBe("Info")
	})

	it.each([
		["IOC Enrichment", "IOC Enrichment"],
		["Portal Branding", "Portal Branding"],
		// The old parent tab of the customer's settings, and a name that is no section.
		["Customer", "Info"],
		["Nope", "Info"]
	])("?tab=%s opens %s", async (tab, section) => {
		tabQuery.value = tab
		const wrapper = render()
		await settle()
		expect(visibleSection(wrapper)).toBe(section)
	})

	it("a link to an admin's section opens Info for anyone else, and mounts nothing of it", async () => {
		signInAs(AuthUserRole.Analyst)
		tabQuery.value = "Security"
		const wrapper = render()
		await settle()
		expect(visibleSection(wrapper)).toBe("Info")
		expect(mounts.Security).toBeUndefined()
	})

	it("follows the link when it changes", async () => {
		const wrapper = render()
		await settle()
		tabQuery.value = "Event Sources"
		await settle()
		expect(visibleSection(wrapper)).toBe("Event Sources")
	})
})

describe("moving between sections", () => {
	it("mounts a section when first opened and keeps it, hidden, when the viewer moves on", async () => {
		tabQuery.value = "Provision"
		const wrapper = render()
		await settle()
		await wrapper.get('[data-testid="rail-item-Security"]').trigger("click")
		await settle()
		expect(visibleSection(wrapper)).toBe("Security")
		await wrapper.get('[data-testid="rail-item-Provision"]').trigger("click")
		await settle()
		expect(visibleSection(wrapper)).toBe("Provision")
		expect(wrapper.find('[data-section="Security"]').exists()).toBe(true)
		expect(mounts).toEqual({ Provision: 1, Security: 1 })
	})

	it("writes the section into the URL on the customer's page, Info as no tab", async () => {
		route.query = { other: "kept" }
		const wrapper = render()
		await settle()
		await wrapper.get('[data-testid="rail-item-Security"]').trigger("click")
		expect(router.replace).toHaveBeenLastCalledWith({ query: { other: "kept", tab: "Security" } })
		route.query = { other: "kept", tab: "Security" }
		await wrapper.get('[data-testid="rail-item-Info"]').trigger("click")
		expect(router.replace).toHaveBeenLastCalledWith({ query: { other: "kept", tab: undefined } })
	})

	it("leaves the URL alone in a modal over another page", async () => {
		const wrapper = render({ routeName: "Customers" })
		await settle()
		await wrapper.get('[data-testid="rail-item-Security"]').trigger("click")
		await settle()
		expect(visibleSection(wrapper)).toBe("Security")
		expect(router.replace).not.toHaveBeenCalled()
	})

	it("opening a group goes back to the section last open in it", async () => {
		tabQuery.value = "Security"
		const wrapper = render()
		await settle()
		await wrapper.get('[data-testid="section-group-data"]').trigger("click")
		await settle()
		expect(visibleSection(wrapper)).toBe("3rd Party Integrations")
		await wrapper.get('[data-testid="section-group-overview"]').trigger("click")
		await settle()
		expect(visibleSection(wrapper)).toBe("Security")
	})
})

describe("the status lights", () => {
	it("reads them once, and again when the viewer leaves a section", async () => {
		tabQuery.value = "IOC Enrichment"
		const wrapper = render()
		await settle()
		expect(getSectionStatus).toHaveBeenCalledTimes(1)
		expect(getSectionStatus).toHaveBeenCalledWith("ACME", expect.any(AbortSignal))
		expect(wrapper.get('[data-testid="section-state"]').text()).toContain("On")
		getSectionStatus.mockResolvedValue(answered(statusFixture({ portal_ioc_enrichment: { on: false } })))
		await wrapper.get('[data-testid="rail-item-SLA"]').trigger("click")
		await settle()
		expect(getSectionStatus).toHaveBeenCalledTimes(2)
		await wrapper.get('[data-testid="rail-item-IOC Enrichment"]').trigger("click")
		await settle()
		expect(wrapper.get('[data-testid="section-state"]').text()).toContain("Off")
	})

	it("a switch shows a light with its word, a list its count", async () => {
		tabQuery.value = "Event Sources"
		const wrapper = render()
		await settle()
		const rail = wrapper.get('[data-testid="customer-sections-rail"]')
		expect(rail.get('[data-testid="rail-item-Event Sources"]').text()).toContain("1")
		expect(rail.get('[data-testid="rail-item-Event Sources"]').text()).toContain("1 source")
		expect(rail.get('[data-testid="rail-item-Network Connectors"]').text()).toContain("None")
		tabQuery.value = "SLA"
		await settle()
		const sla = wrapper.get('[data-testid="rail-item-SLA"]')
		expect(sla.find(".section-led.is-on").exists()).toBe(true)
		expect(sla.text()).toContain("On")
		expect(wrapper.get('[data-testid="rail-item-Activity"]').find(".section-led.is-on").exists()).toBe(false)
	})

	it("a failure leaves the lights off and the sections working", async () => {
		getSectionStatus.mockRejectedValue(new Error("down"))
		tabQuery.value = "SLA"
		const wrapper = render()
		await settle()
		expect(visibleSection(wrapper)).toBe("SLA")
		expect(wrapper.find(".section-led").exists()).toBe(false)
		expect(wrapper.find('[data-testid="section-state"]').exists()).toBe(false)
	})
})

describe("per-viewer conveniences", () => {
	it("pins the open section for this user, and the Pinned menu counts it", async () => {
		tabQuery.value = "Event Sources"
		const wrapper = render()
		await settle()
		const pin = wrapper.get('[data-testid="section-pin"]')
		expect(pin.attributes("aria-pressed")).toBe("false")
		await pin.trigger("click")
		expect(pin.attributes("aria-pressed")).toBe("true")
		expect(JSON.parse(localStorage.getItem(`${PINNED_KEY_PREFIX}ana`) ?? "[]")).toEqual(["Event Sources"])
		expect(wrapper.get('[data-testid="sections-pinned"]').text()).toContain("1")
	})

	it("hides the rail and shows it again, remembered for this browser", async () => {
		const wrapper = render()
		await settle()
		await wrapper.get('[data-testid="rail-hide"]').trigger("click")
		expect(wrapper.find('[data-testid="customer-sections-rail"]').exists()).toBe(false)
		expect(localStorage.getItem(RAIL_HIDDEN_KEY)).toBe("true")
		await wrapper.get('[data-testid="rail-show"]').trigger("click")
		expect(wrapper.find('[data-testid="customer-sections-rail"]').exists()).toBe(true)
		expect(localStorage.getItem(RAIL_HIDDEN_KEY)).toBe("false")
	})
})
