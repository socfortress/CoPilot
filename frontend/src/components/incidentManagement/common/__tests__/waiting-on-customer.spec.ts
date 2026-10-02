import type { Alert } from "@/types/incidentManagement/alerts"
import type { Case } from "@/types/incidentManagement/cases"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider, NPopselect, NSelect } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import AlertBulkStatusButton from "@/components/incidentManagement/alerts/AlertBulkStatusButton.vue"
import AlertsFilters from "@/components/incidentManagement/alerts/AlertsFilters.vue"
import AlertStatusSwitch from "@/components/incidentManagement/alerts/AlertStatusSwitch.vue"
import CaseSeveritySelect from "@/components/incidentManagement/cases/CaseSeveritySelect.vue"
import CaseStatusSwitch from "@/components/incidentManagement/cases/CaseStatusSwitch.vue"
import IncidentAlerts from "@/components/overview/IncidentAlerts.vue"
import IncidentCases from "@/components/overview/IncidentCases.vue"
import { renderStatusLabel } from "../renderStatusLabel"
import StatusIcon from "../StatusIcon.vue"

/**
 * "Waiting on customer" (PENDING_CUSTOMER, #1187) reaches every place an analyst sets
 * or reads a status: the pickers offer it with its explanation and send it as is, the
 * icon and the overview counters show it apart.
 */

const { api, call } = vi.hoisted(() => {
	const api = {
		updateAlertStatus: vi.fn(),
		bulkUpdateAlertStatus: vi.fn(),
		getAvailableUsers: vi.fn(),
		getAlertsList: vi.fn(),
		updateCaseStatus: vi.fn(),
		updateCaseSeverity: vi.fn(),
		getCasesList: vi.fn(),
		getCustomers: vi.fn(),
		getConfiguredSources: vi.fn()
	}
	const call =
		(name: keyof typeof api) =>
		(...args: unknown[]) =>
			api[name](...args)
	return { api, call }
})
vi.mock("@/api", () => ({
	default: {
		incidentManagement: {
			alerts: {
				updateAlertStatus: call("updateAlertStatus"),
				bulkUpdateAlertStatus: call("bulkUpdateAlertStatus"),
				getAvailableUsers: call("getAvailableUsers"),
				getAlertsList: call("getAlertsList")
			},
			cases: {
				updateCaseStatus: call("updateCaseStatus"),
				updateCaseSeverity: call("updateCaseSeverity"),
				getCasesList: call("getCasesList")
			},
			sources: { getConfiguredSources: call("getConfiguredSources") }
		},
		customers: { getCustomers: call("getCustomers") }
	}
}))
vi.mock("@/composables/useGlobalCustomerFilter", async () => {
	const { ref: vueRef } = await import("vue")
	return { useGlobalCustomerFilter: () => ({ globalCustomerCodes: vueRef([]), onGlobalCustomerFilterChange: vi.fn() }) }
})
vi.mock("@/composables/useNavigation", () => ({
	useNavigation: () => ({ routeIncidentManagementAlerts: () => ({ navigate: vi.fn() }), routeIncidentManagementCases: () => ({ navigate: vi.fn() }) })
}))

const alert = { id: 7, status: "OPEN" } as Alert
const caseData = { id: 3, case_status: "IN_PROGRESS", severity: null } as unknown as Case

function inProvider(component: unknown, props: Record<string, unknown>, extra: Record<string, unknown> = {}) {
	return mount(
		defineComponent({
			// The pickers wrap whatever trigger the page passes in their slot.
			setup: () => () =>
				h(NMessageProvider, null, { default: () => h(component as never, props, { default: () => h("button", "trigger") }) })
		}),
		extra
	)
}

function optionValues(component: { props: (name: string) => unknown }) {
	return (component.props("options") as { value: string }[]).map(option => option.value)
}

beforeEach(() => {
	setActivePinia(createPinia())
	for (const mock of Object.values(api)) mock.mockReset()
})

describe("statusIcon", () => {
	it("has an icon of its own for waiting on customer", () => {
		const icon = (status: string | null) => mount(StatusIcon, { props: { status: status as never } }).findComponent({ name: "Icon" }).props("name")
		expect(icon("PENDING_CUSTOMER")).toBe("carbon:pause-outline")
		expect(new Set(["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER", "CLOSED", null].map(icon)).size).toBe(5)
	})
})

describe("status pickers", () => {
	it("the alert switch offers waiting on customer with its help, and sends it", async () => {
		api.updateAlertStatus.mockResolvedValue({ data: { success: true } })
		const wrapper = inProvider(AlertStatusSwitch, { alert })
		const popselect = wrapper.findComponent(NPopselect)
		expect(optionValues(popselect)).toEqual(["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER", "CLOSED"])
		expect(popselect.props("renderLabel")).toBe(renderStatusLabel)
		popselect.vm.$emit("update:value", "PENDING_CUSTOMER")
		await flushPromises()
		expect(api.updateAlertStatus).toHaveBeenCalledWith(7, "PENDING_CUSTOMER")
		expect(wrapper.findComponent(AlertStatusSwitch).emitted("updated")?.[0]).toEqual([{ ...alert, status: "PENDING_CUSTOMER" }])
	})

	it("the case switch sends it without the close confirmation", async () => {
		api.updateCaseStatus.mockResolvedValue({ data: { success: true } })
		const wrapper = inProvider(CaseStatusSwitch, { caseData })
		const popselect = wrapper.findComponent(NPopselect)
		expect(optionValues(popselect)).toContain("PENDING_CUSTOMER")
		popselect.vm.$emit("update:value", "PENDING_CUSTOMER")
		await flushPromises()
		expect(api.updateCaseStatus).toHaveBeenCalledWith(3, "PENDING_CUSTOMER", false)
		expect(wrapper.findComponent(CaseStatusSwitch).emitted("updated")?.[0]).toEqual([{ ...caseData, case_status: "PENDING_CUSTOMER" }])
	})

	it("the bulk button moves only the alerts not already waiting", async () => {
		api.bulkUpdateAlertStatus.mockResolvedValue({ data: { success: true, updated_alert_ids: [1], not_updated_alert_ids: [] } })
		const alerts = [{ id: 1, status: "OPEN" }, { id: 2, status: "PENDING_CUSTOMER" }] as Alert[]
		const wrapper = inProvider(AlertBulkStatusButton, { alerts })
		const popselect = wrapper.findComponent(NPopselect)
		expect(optionValues(popselect)).toContain("PENDING_CUSTOMER")
		popselect.vm.$emit("update:value", "PENDING_CUSTOMER")
		await flushPromises()
		expect(api.bulkUpdateAlertStatus).toHaveBeenCalledWith([1], "PENDING_CUSTOMER")
		expect(wrapper.findComponent(AlertBulkStatusButton).emitted("updated")?.[0]).toEqual([{ id: 1, status: "PENDING_CUSTOMER" }])
	})

	it("the alerts filter can narrow the list to what waits on the customer", async () => {
		const router = createRouter({ history: createMemoryHistory(), routes: [{ path: "/", component: { render: () => null } }] })
		await router.push("/")
		api.getAvailableUsers.mockReturnValue(new Promise(() => {}))
		api.getCustomers.mockReturnValue(new Promise(() => {}))
		api.getConfiguredSources.mockReturnValue(new Promise(() => {}))
		const wrapper = inProvider(
			AlertsFilters,
			{ preset: [{ type: "status", value: "PENDING_CUSTOMER" }] },
			{ global: { plugins: [router] } }
		)
		await flushPromises()
		const select = wrapper.findComponent(NSelect)
		expect(optionValues(select)).toContain("PENDING_CUSTOMER")
		expect(select.props("value")).toBe("PENDING_CUSTOMER")
		expect(wrapper.findComponent(AlertsFilters).emitted("submit")?.[0]).toEqual([[{ type: "status", value: "PENDING_CUSTOMER" }]])
	})
})

describe("caseSeveritySelect", () => {
	it("sets a severity, and clears it so the case follows its alerts again", async () => {
		api.updateCaseSeverity.mockResolvedValue({ data: { success: true } })
		const wrapper = inProvider(CaseSeveritySelect, { caseData: { ...caseData, severity: "High" } })
		const popselect = wrapper.findComponent(NPopselect)
		expect(popselect.props("value")).toBe("High")
		popselect.vm.$emit("update:value", "Critical")
		await flushPromises()
		expect(api.updateCaseSeverity).toHaveBeenLastCalledWith(3, "Critical")
		popselect.vm.$emit("update:value", "__follow__")
		await flushPromises()
		expect(api.updateCaseSeverity).toHaveBeenLastCalledWith(3, null)
		expect(wrapper.findComponent(CaseSeveritySelect).emitted("updated")?.map(([value]) => (value as Case).severity)).toEqual(["Critical", null])
	})

	it("does nothing when the choice is the current one", async () => {
		const wrapper = inProvider(CaseSeveritySelect, { caseData })
		wrapper.findComponent(NPopselect).vm.$emit("update:value", "__follow__")
		await flushPromises()
		expect(api.updateCaseSeverity).not.toHaveBeenCalled()
	})
})

describe("overview counters", () => {
	const CardStatsBars = defineComponent({ name: "CardStatsBars", props: { values: Array }, setup: () => () => h("div") })

	it.each([
		["alerts", IncidentAlerts, "getAlertsList"],
		["cases", IncidentCases, "getCasesList"]
	] as const)("the %s card counts what waits on the customer, so the buckets add up", async (_, card, endpoint) => {
		api[endpoint].mockResolvedValue({ data: { success: true, total: 10, open: 4, in_progress: 3, pending_customer: 2, closed: 1 } })
		const wrapper = inProvider(card, {}, { global: { stubs: { CardStatsBars, CardStatsIcon: true } } })
		await flushPromises()
		const values = wrapper.findComponent(CardStatsBars).props("values") as { label: string; value: number; isTotal?: boolean }[]
		expect(values.find(item => item.label === "Waiting on customer")?.value).toBe(2)
		const buckets = values.filter(item => !item.isTotal).reduce((sum, item) => sum + item.value, 0)
		expect(buckets).toBe(10)
	})
})
