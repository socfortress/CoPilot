import { describe, expect, it } from "vitest"
import {
	filterValueLabel,
	isWaitingOnCustomer,
	statusFilterFromQuery,
	statusSelectOptions,
	workflowStatusLabel
} from "../workflowStatus"

describe("workflow statuses as the customer reads them (#1187)", () => {
	it("words the SOC waiting on the customer from the customer's side", () => {
		expect(workflowStatusLabel("PENDING_CUSTOMER")).toBe("Waiting on you")
		expect(workflowStatusLabel("IN_PROGRESS")).toBe("In Progress")
		expect(workflowStatusLabel("SOMETHING_NEW")).toBe("something new")
		expect(isWaitingOnCustomer("PENDING_CUSTOMER")).toBe(true)
		expect(isWaitingOnCustomer("OPEN")).toBe(false)
	})

	it("never offers the waiting status, but shows it (disabled) while the item is in it", () => {
		expect(statusSelectOptions("OPEN").map(option => option.value)).toEqual(["OPEN", "IN_PROGRESS", "CLOSED"])
		const waiting = statusSelectOptions("PENDING_CUSTOMER")
		expect(waiting.map(option => option.value)).toEqual(["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER", "CLOSED"])
		expect(waiting.find(option => option.value === "PENDING_CUSTOMER")?.disabled).toBe(true)
		expect(waiting.filter(option => option.disabled)).toHaveLength(1)
	})

	it("opens a list filtered on a known status from the query string only", () => {
		expect(statusFilterFromQuery("PENDING_CUSTOMER")).toEqual({ key: "statuses", value: "PENDING_CUSTOMER" })
		expect(statusFilterFromQuery("DROP TABLE")).toEqual({ key: null, value: null })
		expect(statusFilterFromQuery(["OPEN"])).toEqual({ key: null, value: null })
		expect(statusFilterFromQuery(undefined)).toEqual({ key: null, value: null })
	})

	it("labels status values in the list filter, leaving other keys alone", () => {
		expect(filterValueLabel("statuses", "PENDING_CUSTOMER")).toBe("Waiting on you")
		expect(filterValueLabel("sources", "wazuh")).toBe("wazuh")
	})
})
