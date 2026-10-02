import type { SelectOption } from "naive-ui"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider, NSelect } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AlertStatusSelect from "@/components/alerts/AlertStatusSelect.vue"
import CaseStatusSelect from "@/components/cases/CaseStatusSelect.vue"
import CreateCaseForm from "@/components/cases/CreateCaseForm.vue"
import WaitingOnYouNotice from "@/components/common/WaitingOnYouNotice.vue"
import { statusColor, workflowStatus } from "@/components/overview/shared/status"
import { getStatusColor } from "@/utils"

const updateAlertStatus = vi.hoisted(() => vi.fn())
const updateCaseStatus = vi.hoisted(() => vi.fn())
const getCasesFilters = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({
	default: {
		alerts: { updateAlertStatus },
		cases: { updateCaseStatus, getCasesFilters }
	}
}))

beforeEach(() => {
	setActivePinia(createPinia())
	for (const mock of [updateAlertStatus, updateCaseStatus, getCasesFilters]) mock.mockReset()
	getCasesFilters.mockResolvedValue({ data: { assigned_to: [] } })
})

/** Naive UI's message API needs its provider above the component. */
function withMessages(component: object, props: Record<string, unknown>) {
	return mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(component, props)) }))
}

function options(wrapper: ReturnType<typeof mount>) {
	return wrapper.getComponent(NSelect).props("options") as SelectOption[]
}

describe("the SOC waiting on the customer, in the portal (#1187)", () => {
	it("tells the customer the SOC waits on them, and offers to reply", async () => {
		const wrapper = mount(WaitingOnYouNotice, { props: { entity: "case" } })
		expect(wrapper.text()).toContain("The SOC is waiting on your reply")
		expect(wrapper.text()).toContain("this case is paused")
		await wrapper.get("[data-testid=waiting-on-you-reply]").trigger("click")
		expect(wrapper.emitted("reply")).toHaveLength(1)
	})

	for (const [name, component, idProp, update] of [
		["alertStatusSelect", AlertStatusSelect, "alertId", updateAlertStatus],
		["caseStatusSelect", CaseStatusSelect, "caseId", updateCaseStatus]
	] as const) {
		describe(name, () => {
			it("never offers the waiting status on an item that is not in it", () => {
				const wrapper = withMessages(component, { [idProp]: 1, status: "OPEN" })
				expect(options(wrapper).map(option => option.value)).toEqual(["OPEN", "IN_PROGRESS", "CLOSED"])
			})

			it("shows it, disabled, while the item is in it — the customer can only move away", async () => {
				const wrapper = withMessages(component, { [idProp]: 1, status: "PENDING_CUSTOMER" })
				const waiting = options(wrapper).find(option => option.value === "PENDING_CUSTOMER")
				expect(waiting).toMatchObject({ label: "Waiting on you", disabled: true })
				expect(wrapper.getComponent(NSelect).props("value")).toBe("PENDING_CUSTOMER")

				update.mockResolvedValue({ data: {} })
				wrapper.getComponent(NSelect).vm.$emit("update:value", "IN_PROGRESS")
				await flushPromises()
				expect(update).toHaveBeenCalledWith(1, "IN_PROGRESS")
			})
		})
	}

	it("opens a case only in a status the customer may set", async () => {
		const wrapper = withMessages(CreateCaseForm, {})
		await flushPromises()
		const statusSelect = wrapper.findAllComponents(NSelect).find(select =>
			(select.props("options") as SelectOption[] | undefined)?.some(option => option.value === "OPEN")
		)
		expect((statusSelect?.props("options") as SelectOption[]).map(option => option.value)).toEqual([
			"OPEN",
			"IN_PROGRESS",
			"CLOSED"
		])
	})

	it("colours the waiting status in the brand colour, apart from every other state", () => {
		expect(getStatusColor("PENDING_CUSTOMER")).toBe("primary")
		expect(getStatusColor("IN_PROGRESS")).toBe("warning")
		expect(statusColor("PENDING_CUSTOMER")).toBe("primary")
		expect(statusColor("SOMETHING_NEW")).toBe("neutral")
		expect(workflowStatus("PENDING_CUSTOMER")).toEqual({ label: "waiting on you", color: "primary" })
		expect(workflowStatus("IN_PROGRESS")).toEqual({ label: "in progress", color: "warning" })
	})
})
