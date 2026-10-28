import type { Component } from "vue"
import type { PortalCustomer } from "@/types/auth"
import type { IncidentCustomerReport } from "@/types/reports"
import { flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AgentCriticalSelect from "@/components/agents/AgentCriticalSelect.vue"
import AlertComments from "@/components/alerts/AlertDetails/AlertComments.vue"
import AlertStatusSelect from "@/components/alerts/AlertStatusSelect.vue"
import CaseFiles from "@/components/cases/CaseDetails/CaseFiles.vue"
import CaseStatusSelect from "@/components/cases/CaseStatusSelect.vue"
import WaitingOnYouNotice from "@/components/common/WaitingOnYouNotice.vue"
import ReportCard from "@/components/reports/ReportCard.vue"
import { useCustomerPrefill } from "@/composables/common/useCustomerPrefill"
import { useReadOnly } from "@/composables/common/useReadOnly"
import i18n from "@/lang"
import { useAuthStore } from "@/stores/auth"

vi.mock("@/api", () => ({
	default: {
		cases: { getCaseFiles: vi.fn(async () => ({ data: { success: true, case_data_store: [] } })) },
		alerts: {},
		agents: {}
	}
}))

const ACME: PortalCustomer = { customer_code: "ACME", customer_name: "Acme", read_only: true }
const GLOBEX: PortalCustomer = { customer_code: "GLOBEX", customer_name: "Globex" }

function signIn(customers: PortalCustomer[] = [ACME, GLOBEX]) {
	const store = useAuthStore()
	store.customers = customers
	return store
}

function inProviders(component: Component, props: Record<string, unknown>) {
	return mount(
		defineComponent({
			render: () => h(NMessageProvider, () => h(NDialogProvider, () => h(component, props)))
		})
	)
}

/**
 * Read-only portal users (#1312): a user who may only read a customer's data is not offered a
 * control that would change it. The server refuses those writes anyway; this keeps the user from
 * trying, and says why.
 */
describe("read-only portal users", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
	})

	it("are read-only per customer, and file things only under customers they may change", () => {
		const store = signIn()
		expect(store.isReadOnlyFor("ACME")).toBe(true)
		expect(store.isReadOnlyFor("GLOBEX")).toBe(false)
		// An unknown customer is the server's to judge.
		expect(store.isReadOnlyFor("NOPE")).toBe(false)
		expect(store.isReadOnlyFor(null)).toBe(false)
		expect(store.writableCustomers.map(c => c.customer_code)).toEqual(["GLOBEX"])
		expect(store.isReadOnlySomewhere).toBe(true)
		expect(useReadOnly("ACME").value).toBe(true)
	})

	it("are offered and seeded only a customer they may change in a form that files something", () => {
		signIn()
		const writable = useCustomerPrefill({ writable: true })
		expect(writable.customerOptions.value.map(o => o.value)).toEqual(["GLOBEX"])
		expect(writable.hasMultipleCustomers.value).toBe(false)
		expect(writable.initialCustomerCode()).toBe("GLOBEX")
		// A search reads: every customer stays offered.
		expect(useCustomerPrefill().customerOptions.value.map(o => o.value)).toEqual(["ACME", "GLOBEX"])
	})

	it("can't change an alert's, a case's or an agent's state on a read-only customer", () => {
		signIn()
		const disabled = (wrapper: ReturnType<typeof mount>) =>
			wrapper.find(".n-base-selection").classes().includes("n-base-selection--disabled")

		expect(disabled(inProviders(AlertStatusSelect, { alertId: 1, status: "OPEN", customerCode: "ACME" }))).toBe(true)
		expect(disabled(inProviders(AlertStatusSelect, { alertId: 1, status: "OPEN", customerCode: "GLOBEX" }))).toBe(false)
		expect(disabled(inProviders(CaseStatusSelect, { caseId: 1, status: "OPEN", customerCode: "ACME" }))).toBe(true)
		expect(disabled(inProviders(AgentCriticalSelect, { agentId: "001", critical: false, customerCode: "ACME" }))).toBe(true)
	})

	it("see the comments of a read-only customer's alert, but no composer and no edit", () => {
		signIn()
		const store = useAuthStore()
		store.user = { access_token: "t", role: "customer_user", username: "reader", customer_codes: ["ACME"] }
		const alert = {
			id: 7,
			customer_code: "ACME",
			comments: [{ id: 1, alert_id: 7, comment: "mine", user_name: "reader", created_at: "2026-10-27T08:00:00" }]
		}
		const wrapper = inProviders(AlertComments, { alert })
		expect(wrapper.text()).toContain("mine")
		expect(wrapper.find("[data-testid=comment-input]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=read-only-notice]").text()).toBe("You can view this data but not change it.")

		const writable = inProviders(AlertComments, { alert: { ...alert, customer_code: "GLOBEX" } })
		expect(writable.find("[data-testid=comment-input]").exists()).toBe(true)
	})

	it("can't upload a file to a read-only customer's case", async () => {
		signIn()
		const readOnly = inProviders(CaseFiles, { caseId: 3, customerCode: "ACME" })
		const writable = inProviders(CaseFiles, { caseId: 3, customerCode: "GLOBEX" })
		await flushPromises()
		expect(readOnly.find(".n-upload").exists()).toBe(false)
		expect(readOnly.find("[data-testid=read-only-notice]").exists()).toBe(true)
		expect(writable.find(".n-upload").exists()).toBe(true)
	})

	it("can't delete a report of a read-only customer, even one they generated", () => {
		signIn()
		const report: IncidentCustomerReport = {
			id: 5,
			report_name: "Weekly",
			customer_code: "ACME",
			file_name: "weekly.pdf",
			file_size: 2048,
			generated_at: "2026-10-16T09:57:00",
			generated_by: 1,
			generated_by_role: "customer_user",
			date_from: "2026-10-01T00:00:00",
			date_to: "2026-10-16T00:00:00",
			filters_applied: {},
			total_alerts: 0,
			total_cases: 0,
			open_cases: 0,
			closed_cases: 0,
			status: "completed"
		}
		expect(mount(ReportCard, { props: { report } }).text()).not.toContain("Delete")
		expect(mount(ReportCard, { props: { report: { ...report, customer_code: "GLOBEX" } } }).text()).toContain("Delete")
	})

	it("are told someone else must answer the SOC, with no Reply, in their language", () => {
		const wrapper = mount(WaitingOnYouNotice, { props: { entity: "alert", readOnly: true } })
		expect(wrapper.find("[data-testid=waiting-on-you-reply]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=waiting-on-you-read-only]").text()).toContain("a colleague who can change data")
		// No "reply in the comments" for someone who can't (#1312).
		expect(wrapper.text()).toContain("paused until your organization answers.")
		expect(wrapper.text()).not.toContain("Reply in the comments")
		expect(mount(WaitingOnYouNotice, { props: { entity: "alert" } }).find("[data-testid=waiting-on-you-reply]").exists()).toBe(true)

		i18n.global.locale.value = "it"
		const italian = mount(WaitingOnYouNotice, { props: { entity: "alert", readOnly: true } })
		expect(italian.find("[data-testid=waiting-on-you-read-only]").text()).toContain("sola lettura")
	})
})
