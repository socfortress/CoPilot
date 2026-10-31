import { flushPromises, mount } from "@vue/test-utils"
import { NTabs } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AlertDetails from "@/components/alerts/AlertDetails/AlertDetails.vue"
import CaseDetails from "@/components/cases/CaseDetails/CaseDetails.vue"

const getAlert = vi.hoisted(() => vi.fn())
const getCase = vi.hoisted(() => vi.fn())
const askSocEnabledFor = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { alerts: { getAlert }, cases: { getCase } } }))
vi.mock("@/composables/common/useAiReportsAvailability", () => ({
	useAiReportsAvailability: () => ({ isEnabledFor: () => Promise.resolve(false), reset: () => {} })
}))
vi.mock("@/composables/common/useSocRequestsAvailability", () => ({
	useSocRequestsAvailability: () => ({ isEnabledFor: askSocEnabledFor, reset: () => {} })
}))

function stub(name: string) {
	return defineComponent({ name, props: ["entity", "entityId"], emits: ["asked"], setup: () => () => h("div") })
}
const CHILDREN = [
	"AlertOverview",
	"AlertAssets",
	"AlertCases",
	"AlertIocs",
	"AlertAiReport",
	"AlertComments",
	"CaseOverview",
	"CaseAlerts",
	"CaseTasks",
	"CaseTimeline",
	"CaseFiles",
	"CaseComments",
	"AskSoc",
	// Ask Talon about this alert (talon-analyst D97) has its own spec.
	"TalonAskAboutAlert"
]
const stubs = Object.fromEntries(CHILDREN.map(name => [name, stub(name)]))

function alertOf(status: string, customer = "ACME") {
  return {
	data: { alerts: [{ id: 7, status, customer_code: customer, comments: [] }] }
}
}
function caseOf(status: string) {
  return {
	data: { cases: [{ id: 3, case_status: status, customer_code: "ACME", comments: [], alerts: [] }] }
}
}

function tabNames(wrapper: ReturnType<typeof mount>) {
	return wrapper.findAll(".n-tabs-tab").map(tab => tab.text())
}

async function openAskTab(wrapper: ReturnType<typeof mount>) {
	wrapper.getComponent(NTabs).vm.$emit("update:value", "ask-soc")
	await flushPromises()
	return wrapper.getComponent({ name: "AskSoc" })
}

beforeEach(() => {
	setActivePinia(createPinia())
	getAlert.mockReset()
	getCase.mockReset()
	askSocEnabledFor.mockReset()
})

/** "Ask the SOC" on the portal's alert and case pages (#1305): only where the customer allows it. */
describe("the Ask the SOC tab", () => {
	it("is on an alert only when the alert's customer allows it", async () => {
		askSocEnabledFor.mockImplementation(async (code: string) => code === "ACME")
		getAlert.mockResolvedValue(alertOf("OPEN", "OTHER"))
		const off = mount(AlertDetails, { props: { alertId: 7 }, global: { stubs } })
		await flushPromises()
		expect(askSocEnabledFor).toHaveBeenCalledWith("OTHER")
		expect(tabNames(off)).not.toContain("Ask the SOC")

		getAlert.mockResolvedValue(alertOf("OPEN"))
		const on = mount(AlertDetails, { props: { alertId: 7 }, global: { stubs } })
		await flushPromises()
		expect(tabNames(on)).toContain("Ask the SOC")
		const ask = await openAskTab(on)
		expect(ask.props()).toEqual({ entity: "alert", entityId: 7 })
	})

	it("reads the alert again once a question is sent, and tells the list it was handed back", async () => {
		askSocEnabledFor.mockResolvedValue(true)
		getAlert.mockResolvedValueOnce(alertOf("PENDING_CUSTOMER")).mockResolvedValue(alertOf("IN_PROGRESS"))
		const wrapper = mount(AlertDetails, { props: { alertId: 7 }, global: { stubs } })
		await flushPromises()
		const ask = await openAskTab(wrapper)
		ask.vm.$emit("asked", { id: 1 })
		await flushPromises()
		expect(getAlert).toHaveBeenCalledTimes(2)
		expect(wrapper.find("[data-testid=waiting-on-you]").exists()).toBe(false)
		expect(wrapper.emitted("statusUpdated")?.[0]).toEqual([{ alertId: 7, status: "IN_PROGRESS" }])
	})

	it("is on a case only when its customer allows it, and a question re-reads the case", async () => {
		askSocEnabledFor.mockResolvedValue(false)
		getCase.mockResolvedValue(caseOf("OPEN"))
		const off = mount(CaseDetails, { props: { caseId: 3 }, global: { stubs } })
		await flushPromises()
		expect(askSocEnabledFor).toHaveBeenCalledWith("ACME")
		expect(tabNames(off)).not.toContain("Ask the SOC")

		askSocEnabledFor.mockResolvedValue(true)
		getCase.mockReset()
		getCase.mockResolvedValue(caseOf("OPEN"))
		const on = mount(CaseDetails, { props: { caseId: 3 }, global: { stubs } })
		await flushPromises()
		const ask = await openAskTab(on)
		expect(ask.props()).toEqual({ entity: "case", entityId: 3 })
		ask.vm.$emit("asked", { id: 2 })
		await flushPromises()
		expect(getCase).toHaveBeenCalledTimes(2)
		// It was not waiting on the customer: nothing changed for the list.
		expect(on.emitted("statusUpdated")).toBeUndefined()
	})
})
