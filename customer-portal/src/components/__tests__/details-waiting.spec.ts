import { flushPromises, mount } from "@vue/test-utils"
import { NTabs } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AlertDetails from "@/components/alerts/AlertDetails/AlertDetails.vue"
import CaseDetails from "@/components/cases/CaseDetails/CaseDetails.vue"

const getAlert = vi.hoisted(() => vi.fn())
const getCase = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { alerts: { getAlert }, cases: { getCase } } }))
vi.mock("@/composables/common/useAiReportsAvailability", () => ({
	useAiReportsAvailability: () => ({ isEnabledFor: () => Promise.resolve(false), reset: () => {} })
}))

/** The tab contents are other components' business: stand-ins that can emit like them. */
function stub(name: string) {
	return defineComponent({ name, emits: ["added", "updated", "deleted"], setup: () => () => h("div") })
}
const ALERT_CHILDREN = ["AlertOverview", "AlertAssets", "AlertCases", "AlertIocs", "AlertAiReport", "AlertComments"]
const CASE_CHILDREN = ["CaseOverview", "CaseAlerts", "CaseTasks", "CaseTimeline", "CaseFiles", "CaseComments"]
const stubs = (names: string[]) => Object.fromEntries(names.map(name => [name, stub(name)]))

const comment = { id: 9, comment: "yes, that was us", user_name: "portal", created_at: "2026-09-01T10:00:00" }

beforeEach(() => {
	setActivePinia(createPinia())
	getAlert.mockReset()
	getCase.mockReset()
})

describe("the waiting-on-you banner on the detail pages (#1187)", () => {
	describe("alertDetails", () => {
		const alert = (status: string) => ({ data: { alerts: [{ id: 7, status, customer_code: "ACME", comments: [] }] } })

		function mountAlert() {
			return mount(AlertDetails, { props: { alertId: 7 }, global: { stubs: stubs(ALERT_CHILDREN) } })
		}

		it("is absent while the SOC is not waiting on the customer", async () => {
			getAlert.mockResolvedValue(alert("IN_PROGRESS"))
			const wrapper = mountAlert()
			await flushPromises()
			expect(wrapper.find("[data-testid=waiting-on-you]").exists()).toBe(false)
		})

		it("opens the comments on Reply, and a reply hands the alert back", async () => {
			getAlert.mockResolvedValueOnce(alert("PENDING_CUSTOMER")).mockResolvedValueOnce(alert("IN_PROGRESS"))
			const wrapper = mountAlert()
			await flushPromises()
			expect(wrapper.find("[data-testid=waiting-on-you]").exists()).toBe(true)

			await wrapper.get("[data-testid=waiting-on-you-reply]").trigger("click")
			expect(wrapper.getComponent(NTabs).props("value")).toBe("comments")

			wrapper.findComponent({ name: "AlertComments" }).vm.$emit("added", comment)
			await flushPromises()
			expect(getAlert).toHaveBeenCalledTimes(2) // re-read: the backend moved it on
			expect(wrapper.find("[data-testid=waiting-on-you]").exists()).toBe(false)
			expect(wrapper.emitted("statusUpdated")?.[0]).toEqual([{ alertId: 7, status: "IN_PROGRESS" }])
		})

		it("does not re-read an alert that was not waiting when the customer comments", async () => {
			getAlert.mockResolvedValue(alert("OPEN"))
			const wrapper = mountAlert()
			await flushPromises()
			wrapper.getComponent(NTabs).vm.$emit("update:value", "comments") // only the active pane is mounted
			await flushPromises()
			wrapper.findComponent({ name: "AlertComments" }).vm.$emit("added", comment)
			await flushPromises()
			expect(getAlert).toHaveBeenCalledTimes(1)
			expect(wrapper.emitted("statusUpdated")).toBeUndefined()
		})
	})

	describe("caseDetails", () => {
		const caseOf = (status: string) => ({ data: { cases: [{ id: 3, case_status: status, comments: [], alerts: [] }] } })

		function mountCase() {
			return mount(CaseDetails, { props: { caseId: 3 }, global: { stubs: stubs(CASE_CHILDREN) } })
		}

		it("opens the comments on Reply, and a reply hands the case back", async () => {
			getCase.mockResolvedValueOnce(caseOf("PENDING_CUSTOMER")).mockResolvedValueOnce(caseOf("IN_PROGRESS"))
			const wrapper = mountCase()
			await flushPromises()
			expect(wrapper.get("[data-testid=waiting-on-you]").text()).toContain("this case")

			await wrapper.get("[data-testid=waiting-on-you-reply]").trigger("click")
			expect(wrapper.getComponent(NTabs).props("value")).toBe("comments")

			wrapper.findComponent({ name: "CaseComments" }).vm.$emit("added", comment)
			await flushPromises()
			expect(getCase).toHaveBeenCalledTimes(2)
			expect(wrapper.find("[data-testid=waiting-on-you]").exists()).toBe(false)
			expect(wrapper.emitted("statusUpdated")?.[0]).toEqual([{ caseId: 3, status: "IN_PROGRESS" }])
		})

		it("is absent on a case that is not waiting", async () => {
			getCase.mockResolvedValue(caseOf("OPEN"))
			const wrapper = mountCase()
			await flushPromises()
			expect(wrapper.find("[data-testid=waiting-on-you]").exists()).toBe(false)
		})
	})
})
