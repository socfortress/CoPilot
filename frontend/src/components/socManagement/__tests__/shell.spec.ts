import type { PeriodPreset } from "../utils"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import SocFilterBar from "../SocFilterBar.vue"
import SocManagementShell from "../SocManagementShell.vue"
import { dashboard } from "./fixtures"

const getDashboard = vi.fn()
const downloadReport = vi.fn()
const getConfiguredSources = vi.fn()
vi.mock("@/api", () => ({
	default: {
		socManagement: {
			getDashboard: (...args: unknown[]) => getDashboard(...args),
			downloadReport: (...args: unknown[]) => downloadReport(...args)
		},
		incidentManagement: { sources: { getConfiguredSources: (...args: unknown[]) => getConfiguredSources(...args) } }
	}
}))

const saveAs = vi.fn()
vi.mock("file-saver", () => ({ saveAs: (...args: unknown[]) => saveAs(...args) }))

vi.mock("@/composables/useCustomerOptions", () => ({
	useCustomerOptions: () => ({ options: ref([{ label: "Acme Corp (ACME)", value: "ACME" }]), loading: ref(false), load: vi.fn() })
}))

const globalCodes = ref<string[]>([])
vi.mock("@/composables/useGlobalCustomerFilter", () => ({
	useGlobalCustomerFilter: () => ({ globalCustomerCodes: globalCodes, onGlobalCustomerFilterChange: vi.fn() })
}))

// Each tab has its own spec: here they are stand-ins that can raise their events.
function tabStub(name: string, emits: string[] = []) {
	return defineComponent({
		name,
		emits,
		setup:
			(_, { emit }) =>
			() =>
				h("div", { "data-testid": `stub-${name}` }, [
					...emits.map(event =>
						h("button", { "data-testid": `stub-${name}-${event}`, onClick: () => emit(event, event === "focusCustomer" ? "ACME" : "workload") })
					)
				])
	})
}
const stubs = {
	OverviewTab: tabStub("OverviewTab", ["openTab"]),
	SlaTab: tabStub("SlaTab"),
	AnalystsTab: tabStub("AnalystsTab"),
	RulesTab: tabStub("RulesTab"),
	CustomersTab: tabStub("CustomersTab", ["focusCustomer"]),
	WorkloadTab: tabStub("WorkloadTab"),
	PoliciesTab: tabStub("PoliciesTab")
}

async function shell(path = "/soc-management") {
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [{ path: "/soc-management", component: { render: () => null } }]
	})
	await router.push(path)
	await router.isReady()
	const wrapper = mount(
		defineComponent({ setup: () => () => h(NMessageProvider, null, { default: () => h(SocManagementShell) }) }),
		{ global: { plugins: [router], stubs } }
	)
	await flushPromises()
	return { wrapper, router }
}

beforeEach(() => {
	setActivePinia(createPinia())
	vi.useFakeTimers({ toFake: ["Date"] })
	vi.setSystemTime(new Date("2026-09-30T10:00:00Z"))
	for (const mock of [getDashboard, downloadReport, getConfiguredSources, saveAs]) mock.mockReset()
	getDashboard.mockResolvedValue({ data: dashboard() })
	getConfiguredSources.mockResolvedValue({ data: { sources: ["wazuh"] } })
	globalCodes.value = []
})
afterEach(() => vi.useRealTimers())

describe("socManagementShell", () => {
	it("loads the snapshot for the URL's filters and opens on the overview", async () => {
		const { wrapper } = await shell("/soc-management?period=7d&customer=ACME")
		expect(getDashboard).toHaveBeenCalledTimes(1)
		const query = getDashboard.mock.calls[0][0]
		expect(query.customerCodes).toEqual(["ACME"])
		expect(query.dateTo.getTime() - query.dateFrom.getTime()).toBe(7 * 86_400_000)
		expect(wrapper.find("[data-testid=stub-OverviewTab]").exists()).toBe(true)
		expect(wrapper.text()).toContain("ACME")
	})

	it("keeps the tab in the URL, both ways", async () => {
		const { wrapper, router } = await shell("/soc-management?tab=rules")
		expect(wrapper.find("[data-testid=stub-RulesTab]").exists()).toBe(true)
		await wrapper.get("[data-testid=soc-tab-sla]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query.tab).toBe("sla")
		expect(wrapper.find("[data-testid=stub-SlaTab]").exists()).toBe(true)
	})

	it("follows a tab's request to open another, and focuses a customer from the customers tab", async () => {
		const { wrapper, router } = await shell("/soc-management")
		await wrapper.get("[data-testid=stub-OverviewTab-openTab]").trigger("click")
		await flushPromises()
		expect(router.currentRoute.value.query.tab).toBe("workload")

		await router.replace({ query: { tab: "customers" } })
		await flushPromises()
		await wrapper.get("[data-testid=stub-CustomersTab-focusCustomer]").trigger("click")
		await flushPromises()
		expect([router.currentRoute.value.query.customer].flat()).toEqual(["ACME"])
		expect(router.currentRoute.value.query.tab).toBe("overview")
	})

	it("explains when SLA tracking began inside the period", async () => {
		getDashboard.mockResolvedValue({ data: dashboard({ tracking_since: "2026-09-20T08:00:00" }) })
		const { wrapper } = await shell("/soc-management")
		expect(wrapper.get("[data-testid=tracking-notice]").text()).toContain("SLA tracking began")
	})

	it("says when the dashboard could not be loaded", async () => {
		getDashboard.mockImplementation(() => Promise.reject(Object.assign(new Error("boom"), { response: { data: { detail: "unavailable" } } })))
		const { wrapper } = await shell("/soc-management")
		expect(wrapper.get("[data-testid=soc-error]").text()).toContain("unavailable")
	})

	it("downloads the report named after the period", async () => {
		downloadReport.mockResolvedValue({ data: new Blob(["%PDF"]) })
		const { wrapper } = await shell("/soc-management?period=7d")
		await wrapper.get("[data-testid=soc-export]").trigger("click")
		await flushPromises()
		expect(saveAs).toHaveBeenCalledWith(expect.any(Blob), "soc_report_2026-09-23_2026-09-30.pdf")
	})

	it("refresh reloads even when the window lands on the same minute", async () => {
		const { wrapper } = await shell("/soc-management")
		await wrapper.get("[data-testid=soc-refresh]").trigger("click")
		await flushPromises()
		expect(getDashboard).toHaveBeenCalledTimes(2)
	})

	it("starts from the sidebar's customer filter when the URL names none", async () => {
		globalCodes.value = ["GLOBEX"]
		await shell("/soc-management")
		expect(getDashboard.mock.calls.at(-1)?.[0].customerCodes).toEqual(["GLOBEX"])
	})
})

describe("socFilterBar", () => {
	function bar() {
		const preset = ref<PeriodPreset>("30d")
		const wrapper = mount(SocFilterBar, {
			props: {
				preset: preset.value,
				"onUpdate:preset": (value: PeriodPreset) => {
					preset.value = value
				},
				customerCodes: [],
				severities: [],
				sources: [],
				customRange: null,
				range: { from: new Date("2026-09-01T00:00:00Z"), to: new Date("2026-09-30T00:00:00Z") },
				customerOptions: [],
				sourceOptions: []
			}
		})
		return { wrapper, preset }
	}

	it("marks the active period and picks another", async () => {
		const { wrapper, preset } = bar()
		expect(wrapper.get("[data-testid=period-30d]").attributes("aria-checked")).toBe("true")
		await wrapper.get("[data-testid=period-7d]").trigger("click")
		expect(preset.value).toBe("7d")
	})

	it("starts a custom period from the window on screen", async () => {
		const { wrapper, preset } = bar()
		await wrapper.get("[data-testid=period-custom]").trigger("click")
		expect(preset.value).toBe("30d") // the parent switches once it has a range
		expect(wrapper.emitted("customRange")?.[0]).toEqual([
			{ from: new Date("2026-09-01T00:00:00Z"), to: new Date("2026-09-30T00:00:00Z") }
		])
	})
})
