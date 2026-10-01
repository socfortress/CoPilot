import type { AlertStatus } from "@/types/incidentManagement/alerts"
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import { defineComponent } from "vue"
import { renderStatusLabel } from "../renderStatusLabel"
import { PENDING_CUSTOMER_HELP, STATUS_LABELS, STATUS_OPTIONS, STATUS_ORDER, statusColor, statusLabel } from "../status"

describe("incident statuses", () => {
	it("offers every status once, in workflow order, waiting on customer before closed", () => {
		expect(STATUS_OPTIONS.map(o => o.value)).toEqual(["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER", "CLOSED"])
		expect(new Set(STATUS_ORDER).size).toBe(Object.keys(STATUS_LABELS).length)
	})

	it("labels statuses for people, leaving unknown values readable", () => {
		expect(statusLabel("PENDING_CUSTOMER")).toBe("Waiting on customer")
		expect(statusLabel("IN_PROGRESS")).toBe("In progress")
		expect(statusLabel("SOMETHING_NEW")).toBe("SOMETHING_NEW")
		expect(statusLabel(null)).toBe("n/d")
		expect(statusLabel("")).toBe("n/d")
	})

	it("never colours waiting on customer, or an unknown status, as closed", () => {
		const colors = Object.fromEntries(STATUS_ORDER.map(s => [s, statusColor(s)])) as Record<AlertStatus, string>
		expect(colors).toEqual({ OPEN: "danger", IN_PROGRESS: "warning", PENDING_CUSTOMER: "primary", CLOSED: "success" })
		expect(statusColor("SOMETHING_NEW")).toBeUndefined()
		expect(statusColor(null)).toBeUndefined()
	})

	it("explains in the picker that waiting on the customer stops the SLA clocks", () => {
		expect(PENDING_CUSTOMER_HELP).toMatch(/SLA clocks stop/)
		const Host = defineComponent({ render: () => renderStatusLabel({ label: "Waiting on customer", value: "PENDING_CUSTOMER" }) })
		const wrapper = mount(Host)
		expect(wrapper.text()).toContain("Waiting on customer")
		expect(wrapper.find("[data-testid=pending-customer-help]").exists()).toBe(true)
		expect(renderStatusLabel({ label: "Open", value: "OPEN" })).toBe("Open")
	})
})
